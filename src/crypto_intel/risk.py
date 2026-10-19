"""Risk gates with adaptive anomaly, correlation, multi-TF, and VaR awareness (v0.12). Strategies propose; this module decides."""

from __future__ import annotations

from crypto_intel.models import AssetClass, RiskDecision, Side, Signal
from crypto_intel.regime import anomaly_score, historical_var

CLASS_LIMITS: dict[AssetClass, float] = {
    AssetClass.MAJOR: 0.08,
    AssetClass.LARGE_CAP_ALT: 0.04,
    AssetClass.STABLECOIN: 0.0,
    AssetClass.DEFI: 0.02,
    AssetClass.MEME: 0.005,
    AssetClass.L2: 0.03,
    AssetClass.RWA: 0.02,
    AssetClass.PERPETUAL: 0.02,
}

MIN_CONFIDENCE = {
    AssetClass.MAJOR: 0.55,
    AssetClass.LARGE_CAP_ALT: 0.60,
    AssetClass.STABLECOIN: 0.50,
    AssetClass.DEFI: 0.65,
    AssetClass.MEME: 0.75,
    AssetClass.L2: 0.60,
    AssetClass.RWA: 0.60,
    AssetClass.PERPETUAL: 0.65,
}


def evaluate(
    signal: Signal,
    *,
    kill_switch: bool = False,
    drawdown: float = 0.0,
    max_drawdown: float = 0.12,
    gap_pct: float = 0.0,
    anomaly: float = 0.0,
    var_95: float = 0.0,
    multi_tf_ok: bool = True,
) -> RiskDecision:
    reasons: list[str] = []
    if kill_switch:
        reasons.append("kill switch engaged")
    if drawdown >= max_drawdown:
        reasons.append("max drawdown halt")
    if signal.asset_class is AssetClass.RWA and abs(gap_pct) > 0.08:
        reasons.append("rwa gap halt")
    if signal.asset_class is AssetClass.STABLECOIN and signal.side is not Side.ALERT:
        reasons.append("stablecoins are monitor-only")
    if signal.confidence < MIN_CONFIDENCE[signal.asset_class]:
        reasons.append("confidence below class threshold")
    if anomaly > 0.7:
        reasons.append("high anomaly score")
    if var_95 > 0.08:
        reasons.append("elevated historical VaR")
    if not multi_tf_ok and signal.side is Side.LONG:
        reasons.append("multi-timeframe mismatch")
    cap = CLASS_LIMITS[signal.asset_class]
    size = min(signal.size_fraction, cap)
    if anomaly > 0.5:
        size *= 0.50
    if var_95 > 0.05:
        size *= 0.70
    if signal.side is Side.ALERT:
        reasons.append("monitor only, no order")
    if signal.side is Side.FLAT:
        size = 0.0
    if reasons:
        return RiskDecision(False, 0.0, tuple(reasons))
    if size <= 0 and signal.side is Side.LONG:
        reasons.append("class size cap is zero")
        return RiskDecision(False, 0.0, tuple(reasons))
    return RiskDecision(True, round(size, 4), ("within class limits and enhanced VaR/anomaly/multi-TF gates",))
