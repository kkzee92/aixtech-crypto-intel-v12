"""Shared multi-scale market-regime classifier with volatility tier, enhanced anomaly, and multi-timeframe helpers (v0.12)."""

from __future__ import annotations

from enum import Enum
from statistics import fmean, pstdev

from crypto_intel.models import Candle


class Regime(str, Enum):
    TREND = "trend"
    RANGE = "range"
    STRESS = "stress"


class VolatilityTier(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


def atr_pct(candles: list[Candle], bars: int = 8) -> float:
    window = candles[-bars:]
    ranges = [(c.high - c.low) / c.close for c in window if c.close]
    return fmean(ranges) if ranges else 0.0


def classify(candles: list[Candle]) -> Regime:
    """Stress first (short ATR), then medium-span trend vs range."""
    if len(candles) < 8:
        raise ValueError("need at least 8 candles")
    width = atr_pct(candles, 8)
    if width >= 0.035:
        return Regime.STRESS
    closes = [c.close for c in candles]
    span_short = closes[-1] / closes[-8] - 1.0
    span_med = closes[-1] / closes[-min(20, len(closes))] - 1.0 if len(closes) >= 12 else span_short
    if abs(span_short) >= 0.025 or abs(span_med) >= 0.04:
        return Regime.TREND
    return Regime.RANGE


def volatility_tier(candles: list[Candle]) -> VolatilityTier:
    width = atr_pct(candles, 14)
    if width >= 0.045:
        return VolatilityTier.HIGH
    if width <= 0.018:
        return VolatilityTier.LOW
    return VolatilityTier.NORMAL


def multi_timeframe_aligned(candles: list[Candle], short: int = 6, med: int = 12) -> bool:
    """Simple multi-TF consistency: short and medium returns same sign and positive for trend."""
    if len(candles) < med:
        return False
    closes = [c.close for c in candles]
    short_ret = closes[-1] / closes[-short] - 1.0
    med_ret = closes[-1] / closes[-med] - 1.0
    return short_ret > 0 and med_ret > 0 and abs(short_ret) > 0.005


def anomaly_score(candles: list[Candle]) -> float:
    """Enhanced multi-stat anomaly 0-1 research score including kurtosis proxy. Higher = more anomalous."""
    if len(candles) < 10:
        return 0.0
    closes = [c.close for c in candles[-20:]]
    volumes = [c.volume for c in candles[-20:]]
    rets = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
    if not rets:
        return 0.0
    mean_r = fmean(rets)
    std_r = pstdev(rets) if len(rets) > 1 else 0.001
    last_z = abs(rets[-1] - mean_r) / max(std_r, 0.001)
    mean_v = fmean(volumes)
    std_v = pstdev(volumes) if len(volumes) > 1 else 1
    vol_z = abs(volumes[-1] - mean_v) / max(std_v, 1)
    consecutive = sum(1 for r in rets[-3:] if abs(r) > 0.03)
    skew = sum((r - mean_r)**3 for r in rets) / (len(rets) * std_r**3) if std_r else 0
    kurt = sum((r - mean_r)**4 for r in rets) / (len(rets) * std_r**4) - 3 if std_r else 0
    score = min(1.0, (last_z / 4.0) * 0.30 + (vol_z / 3.0) * 0.20 + (consecutive / 3.0) * 0.20 + (abs(skew) / 2.0) * 0.15 + (max(0, kurt) / 5.0) * 0.15)
    return round(score, 3)


def historical_var(candles: list[Candle], confidence: float = 0.95, window: int = 20) -> float:
    """Simple historical VaR proxy on returns (positive number for loss magnitude)."""
    if len(candles) < window:
        return 0.05
    closes = [c.close for c in candles[-window:]]
    rets = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
    if not rets:
        return 0.05
    rets.sort()
    idx = int((1 - confidence) * len(rets))
    return abs(rets[max(0, idx)])
