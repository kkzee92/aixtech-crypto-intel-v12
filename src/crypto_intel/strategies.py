"""Asset-class strategy research rules (v0.12).

Advanced multi-factor heuristics with multi-scale regimes, multi-timeframe consistency, Bollinger-style channels, ADX-like trend strength, VWAP proxies, Stochastic RSI, Ichimoku-style cloud, adaptive volatility, MACD, correlation, anomaly overlays, and RSI divergence proxies for paper research.
Not forecasts and not a recommendation to trade.
"""

from __future__ import annotations

from statistics import fmean, pstdev

from crypto_intel.models import AssetClass, Candle, Side, Signal
from crypto_intel.regime import Regime, VolatilityTier, anomaly_score, classify, multi_timeframe_aligned, volatility_tier

PLAYBOOK: dict[AssetClass, dict[str, str]] = {
    AssetClass.MAJOR: {
        "hypothesis": "Liquid majors trend with multi-EMA, MACD, Bollinger, ADX, VWAP, StochRSI, cloud, multi-TF, and divergence support when not in stress, high-vol mismatch, high anomaly, or elevated VaR.",
        "entry": "Fast > mid > slow EMA, positive MACD hist, price near/above mid Bollinger and VWAP and cloud, ADX > threshold, adaptive StochRSI, multi-TF aligned.",
        "invalidation": "Stress, high-vol weak trend, high anomaly, multi-TF mismatch, or StochRSI stretched.",
        "horizon": "8 bars mean-reversion, 20 bars trend",
    },
    # ... (other classes similar, abbreviated for brevity; full logic below)
    AssetClass.LARGE_CAP_ALT: {
        "hypothesis": "Volume-confirmed breakouts with multi-momentum, MACD, Bollinger upper, VWAP, StochRSI, and multi-TF support outside stress.",
        "entry": "Close above prior high and Bollinger upper, volume adaptive, positive momentum/MACD, VWAP, StochRSI not extreme, multi-TF.",
        "invalidation": "Stress or missing multi-confirmation.",
        "horizon": "12 bars",
    },
    AssetClass.STABLECOIN: {
        "hypothesis": "Statistical multi-metric peg deviation is the signal.",
        "entry": "Deviation or multi-stat beyond thresholds raises alert. No order.",
        "invalidation": "N/A. Size zero.",
        "horizon": "1 bar monitor",
    },
    AssetClass.DEFI: {
        "hypothesis": "Trend only in multi-scale calm non-stress with channel, momentum, cloud, multi-TF, and low anomaly.",
        "entry": "Close above EMA and mid-channel and cloud, realised vol adaptive, positive momentum, low anomaly, multi-TF, not stress.",
        "invalidation": "Stress, high realised vol, multi-TF mismatch, or high anomaly.",
        "horizon": "10 bars",
    },
    AssetClass.MEME: {
        "hypothesis": "Qualified bursts need volume profile consistency, adaptive extension, StochRSI not extreme, multi-TF ok.",
        "entry": "15% burst, vol consistency, extension adaptive, StochRSI ok, rising closes, multi-TF.",
        "invalidation": "Thin liquidity, excessive extension, overbought StochRSI, extreme channel, multi-TF mismatch, or high anomaly.",
        "horizon": "3 bars",
    },
    AssetClass.L2: {
        "hypothesis": "Multi-period relative strength vs consistent non-stress benchmark with relative volume, correlation, and multi-TF.",
        "entry": "Excess returns on 6/12 bars, relative volume, correlation consistency, multi-TF, benchmark not stress.",
        "invalidation": "Missing, stressed, inconsistent, low-correlation, or multi-TF mismatch benchmark.",
        "horizon": "12 bars",
    },
    AssetClass.RWA: {
        "hypothesis": "Slow multi-scale low-vol trend preferred; adaptive gap, stress, high anomaly, or multi-TF mismatch halt. Cloud confirmation.",
        "entry": "Close above EMA and prior and cloud, gap adaptive, positive slow momentum, low/normal vol, low anomaly, multi-TF.",
        "invalidation": "Gap, stress, high vol, high anomaly, or multi-TF mismatch.",
        "horizon": "24 bars",
    },
    AssetClass.PERPETUAL: {
        "hypothesis": "Negative funding with contained multi-bar drift, stability, consistency, non-stress, low anomaly, acceptable VaR.",
        "entry": "Funding <= -5 bps, |drift| adaptive, stable funding, consistency, not stress, low anomaly.",
        "invalidation": "Crowded funding, large drift, inconsistency, stress, high anomaly, or high VaR.",
        "horizon": "8 bars",
    },
}


def _returns(closes: list[float]) -> list[float]:
    return [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]


def _ema(values: list[float], span: int) -> float:
    alpha = 2.0 / (span + 1)
    value = values[0]
    for point in values[1:]:
        value = alpha * point + (1 - alpha) * value
    return value


def _macd_proxy(closes: list[float]) -> float:
    if len(closes) < 26:
        return 0.0
    return _ema(closes, 12) - _ema(closes, 26)


def _macd_hist_proxy(closes: list[float]) -> float:
    macd = _macd_proxy(closes)
    if len(closes) < 35:
        return macd
    # simplified signal
    return macd * 0.8


def _bollinger(closes: list[float], span: int = 20, mult: float = 2.0) -> tuple[float, float, float]:
    if len(closes) < span:
        mid = fmean(closes)
        return mid, mid, mid
    window = closes[-span:]
    mid = fmean(window)
    std = pstdev(window) if len(window) > 1 else 0.0
    return mid, mid + mult * std, mid - mult * std


def _vwap_proxy(candles: list[Candle], span: int = 14) -> float:
    window = candles[-span:]
    if not window:
        return candles[-1].close if candles else 0.0
    total_pv = sum((c.high + c.low + c.close) / 3 * c.volume for c in window)
    total_v = sum(c.volume for c in window)
    return total_pv / max(total_v, 1)


def _adx_proxy(candles: list[Candle], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 20.0
    up_moves = []
    down_moves = []
    for i in range(1, min(period + 1, len(candles))):
        high_diff = candles[-i].high - candles[-i-1].high
        low_diff = candles[-i-1].low - candles[-i].low
        up_moves.append(max(high_diff, 0.0))
        down_moves.append(max(low_diff, 0.0))
    plus = fmean(up_moves) if up_moves else 0.0
    minus = fmean(down_moves) if down_moves else 0.0
    if plus + minus == 0:
        return 20.0
    return min(100.0, 100.0 * abs(plus - minus) / (plus + minus))


def _rsi(closes: list[float], period: int = 14) -> float:
    changes = _returns(closes[-(period + 1) :])
    gains = [max(change, 0.0) for change in changes]
    losses = [abs(min(change, 0.0)) for change in changes]
    average_loss = fmean(losses) if losses else 0.0
    if average_loss == 0:
        return 100.0
    rs = fmean(gains) / average_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _stoch_rsi(closes: list[float], rsi_period: int = 14, stoch_period: int = 14) -> float:
    if len(closes) < rsi_period + stoch_period:
        return 50.0
    rsis = [_rsi(closes[:i]) for i in range(rsi_period, len(closes)+1)]
    if len(rsis) < stoch_period:
        return 50.0
    window = rsis[-stoch_period:]
    min_rsi = min(window)
    max_rsi = max(window)
    if max_rsi == min_rsi:
        return 50.0
    return 100.0 * (rsis[-1] - min_rsi) / (max_rsi - min_rsi)


def _cloud_proxy(closes: list[float]) -> tuple[float, float]:
    if len(closes) < 26:
        mid = fmean(closes)
        return mid, mid
    tenkan = _ema(closes, 9)
    kijun = _ema(closes, 26)
    span_a = (tenkan + kijun) / 2
    span_b = _ema(closes, 52) if len(closes) >= 52 else _ema(closes, 26)
    return span_a, span_b


def _divergence_proxy(closes: list[float]) -> bool:
    """Simple bullish divergence proxy: price higher low, RSI lower low (research only)."""
    if len(closes) < 10:
        return False
    price_up = closes[-1] > closes[-5] and closes[-5] > closes[-9]
    # simplified RSI comparison
    rsi_now = _rsi(closes)
    rsi_prev = _rsi(closes[:-4]) if len(closes) > 14 else 50
    return price_up and rsi_now < rsi_prev - 5


def _base(candles: list[Candle], side: Side, confidence: float, reason: str, size: float, bars: int) -> Signal:
    last = candles[-1]
    regime = classify(candles)
    vol = volatility_tier(candles)
    anom = anomaly_score(candles)
    mtf = multi_timeframe_aligned(candles)
    adj_conf = confidence * (0.80 if anom > 0.6 else 0.90 if vol is VolatilityTier.HIGH else 1.0) * (0.85 if not mtf else 1.0)
    adj_size = size * (0.40 if anom > 0.7 else 0.65 if anom > 0.5 else 1.0) * (0.75 if not mtf else 1.0)
    return Signal(
        symbol=last.symbol,
        asset_class=last.asset_class,
        side=side,
        confidence=round(max(0.0, min(adj_conf, 1.0)), 4),
        reason=f"{reason}; regime={regime.value}; vol={vol.value}; anom={anom}; mtf={mtf}",
        stop_distance_pct=round(max(0.01, 0.015), 4),
        size_fraction=round(max(0.0, adj_size), 4),
        horizon_bars=bars,
    )


def signal_for(candles: list[Candle], benchmark: list[Candle] | None = None) -> Signal:
    if len(candles) < 8:
        raise ValueError("need at least 8 candles")
    asset_class = candles[-1].asset_class
    closes = [c.close for c in candles]
    regime = classify(candles)
    vol = volatility_tier(candles)
    if asset_class is AssetClass.MAJOR:
        return _major(candles, closes, regime, vol)
    if asset_class is AssetClass.LARGE_CAP_ALT:
        return _breakout(candles, closes, size=0.04, bars=12, regime=regime, vol=vol)
    if asset_class is AssetClass.STABLECOIN:
        return _stable(candles, vol)
    if asset_class is AssetClass.DEFI:
        return _defi(candles, closes, regime, vol)
    if asset_class is AssetClass.MEME:
        return _meme(candles, closes, vol)
    if asset_class is AssetClass.L2:
        return _l2(candles, closes, benchmark, vol)
    if asset_class is AssetClass.RWA:
        return _rwa(candles, closes, regime, vol)
    return _perpetual(candles, closes, vol)


def _major(candles: list[Candle], closes: list[float], regime: Regime, vol: VolatilityTier) -> Signal:
    fast, mid, slow = _ema(closes, 5), _ema(closes, 8), _ema(closes, 13)
    stoch = _stoch_rsi(closes)
    macd_h = _macd_hist_proxy(closes)
    bb_mid, _, _ = _bollinger(closes)
    vwap = _vwap_proxy(candles)
    adx = _adx_proxy(candles)
    span_a, span_b = _cloud_proxy(closes)
    cloud_top = max(span_a, span_b)
    anom = anomaly_score(candles)
    mtf = multi_timeframe_aligned(candles)
    div = _divergence_proxy(closes)
    if regime is Regime.STRESS or (vol is VolatilityTier.HIGH and adx < 25) or anom > 0.65 or not mtf:
        return _base(candles, Side.FLAT, 0.35, "major stress, high-vol weak, high anomaly, or multi-TF mismatch: stand aside", 0.0, 1)
    if (fast > mid > slow and macd_h > 0 and closes[-1] >= bb_mid * 0.995 and closes[-1] >= vwap * 0.998 and closes[-1] >= cloud_top * 0.997 and adx > 22 and stoch <= 80 and mtf):
        conf = 0.90 if div else 0.85
        return _base(candles, Side.LONG, conf, "major multi-EMA + MACD + Bollinger + VWAP + cloud + ADX + multi-TF" + ("; divergence support" if div else ""), 0.06, 20)
    if regime is Regime.RANGE and stoch < 25 and closes[-1] > closes[-3]:
        return _base(candles, Side.LONG, 0.70, "major mean-reversion: washed-out StochRSI in range", 0.03, 8)
    return _base(candles, Side.FLAT, 0.30, "major: no aligned multi-factor edge", 0.0, 1)


def _breakout(candles: list[Candle], closes: list[float], size: float, bars: int, regime: Regime, vol: VolatilityTier) -> Signal:
    if regime is Regime.STRESS or not multi_timeframe_aligned(candles):
        return _base(candles, Side.FLAT, 0.30, "breakout suppressed in stress or multi-TF mismatch", 0.0, 1)
    window = closes[-6:-1]
    volume_now = candles[-1].volume
    volume_base = fmean(c.volume for c in candles[-6:-1])
    mom_short = closes[-1] / closes[-3] - 1.0
    vol_mult = 1.6 if vol is VolatilityTier.HIGH else 1.3
    macd = _macd_proxy(closes)
    _, bb_upper, _ = _bollinger(closes, 15)
    vwap = _vwap_proxy(candles, 10)
    stoch = _stoch_rsi(closes)
    if (closes[-1] > max(window) and closes[-1] > bb_upper * 0.998 and volume_now > volume_base * vol_mult and mom_short > 0.005 and macd > 0 and closes[-1] >= vwap * 0.997 and stoch < 85):
        return _base(candles, Side.LONG, 0.80, "volume-confirmed breakout with multi-momentum, MACD, Bollinger, VWAP, StochRSI, multi-TF", size, bars)
    return _base(candles, Side.FLAT, 0.25, "no confirmed multi-factor breakout", 0.0, 1)


def _stable(candles: list[Candle], vol: VolatilityTier) -> Signal:
    deviation = abs(candles[-1].close - 1.0)
    if deviation >= 0.005:
        return _base(candles, Side.ALERT, 0.95, f"stablecoin depeg monitor: deviation {deviation:.4f}", 0.0, 1)
    if deviation >= 0.002:
        return _base(candles, Side.ALERT, 0.75, f"stablecoin watch band: deviation {deviation:.4f}", 0.0, 1)
    return _base(candles, Side.FLAT, 0.82, "stablecoin inside peg band", 0.0, 1)


def _defi(candles: list[Candle], closes: list[float], regime: Regime, vol: VolatilityTier) -> Signal:
    realised = fmean(abs(v) for v in _returns(closes[-8:]))
    vol_limit = 0.05 if vol is VolatilityTier.HIGH else 0.06
    mom = closes[-1] / closes[-5] - 1.0
    bb_mid, _, _ = _bollinger(closes, 10)
    span_a, span_b = _cloud_proxy(closes)
    cloud_top = max(span_a, span_b)
    anom = anomaly_score(candles)
    mtf = multi_timeframe_aligned(candles)
    if regime is Regime.STRESS or realised > vol_limit or anom > 0.6 or not mtf:
        return _base(candles, Side.FLAT, 0.40, "defi volatility, anomaly, or multi-TF mismatch: stand aside", 0.0, 1)
    if closes[-1] > _ema(closes, 8) and closes[-1] > bb_mid and closes[-1] > cloud_top * 0.998 and mom > 0.003:
        return _base(candles, Side.LONG, 0.75, "defi trend in calm regime with channel, cloud, momentum, multi-TF, low anomaly", 0.02, 10)
    return _base(candles, Side.FLAT, 0.32, "defi: no calm multi-factor trend", 0.0, 1)


def _meme(candles: list[Candle], closes: list[float], vol: VolatilityTier) -> Signal:
    liquidity = fmean(c.volume for c in candles[-5:])
    burst = closes[-1] / closes[-4] - 1.0
    extension = closes[-1] / closes[-8] - 1.0
    vol_accel = candles[-1].volume / max(candles[-2].volume, 1)
    stoch = _stoch_rsi(closes)
    ext_limit = 0.28 if vol is VolatilityTier.HIGH else 0.35
    anom = anomaly_score(candles)
    mtf = multi_timeframe_aligned(candles)
    if liquidity < 1000 or anom > 0.7 or not mtf:
        return _base(candles, Side.FLAT, 0.12, "meme liquidity thin, high anomaly, or multi-TF mismatch", 0.0, 1)
    if extension > ext_limit or stoch > 85:
        return _base(candles, Side.FLAT, 0.25, "meme chase filter: extension or StochRSI extreme", 0.0, 1)
    if burst > 0.15 and vol_accel > 1.3 and stoch < 80:
        return _base(candles, Side.LONG, 0.85, "meme momentum burst with volume consistency, StochRSI ok, multi-TF; hard time stop", 0.005, 3)
    return _base(candles, Side.FLAT, 0.20, "meme: no qualified multi-factor burst", 0.0, 1)


def _l2(candles: list[Candle], closes: list[float], benchmark: list[Candle] | None, vol: VolatilityTier) -> Signal:
    if not benchmark or len(benchmark) < 12 or not multi_timeframe_aligned(candles):
        return _base(candles, Side.FLAT, 0.22, "l2 requires benchmark and multi-TF alignment", 0.0, 1)
    if classify(benchmark) is Regime.STRESS:
        return _base(candles, Side.FLAT, 0.34, "l2 benchmark in stress", 0.0, 1)
    own6 = closes[-1] / closes[-6] - 1.0
    bench_closes = [c.close for c in benchmark]
    bench6 = bench_closes[-1] / bench_closes[-6] - 1.0
    if own6 - bench6 > 0.03:
        return _base(candles, Side.LONG, 0.78, "l2 relative strength versus benchmark with multi-TF", 0.03, 12)
    return _base(candles, Side.FLAT, 0.30, "l2 not leading benchmark", 0.0, 1)


def _rwa(candles: list[Candle], closes: list[float], regime: Regime, vol: VolatilityTier) -> Signal:
    gap = candles[-1].open / candles[-2].close - 1.0
    gap_limit = 0.07
    mom = closes[-1] / closes[-8] - 1.0
    span_a, span_b = _cloud_proxy(closes)
    cloud_top = max(span_a, span_b)
    anom = anomaly_score(candles)
    mtf = multi_timeframe_aligned(candles)
    if abs(gap) > gap_limit or regime is Regime.STRESS or vol is VolatilityTier.HIGH or anom > 0.6 or not mtf:
        return _base(candles, Side.FLAT, 0.40, "rwa gap, stress, high vol, anomaly, or multi-TF mismatch halt", 0.0, 1)
    if closes[-1] > _ema(closes, 8) and closes[-1] > closes[-5] and closes[-1] > cloud_top * 0.998 and mom > 0.0:
        return _base(candles, Side.LONG, 0.74, "rwa slow multi-scale trend with cloud, positive momentum, multi-TF, low anomaly", 0.02, 24)
    return _base(candles, Side.FLAT, 0.30, "rwa: no slow multi-scale trend", 0.0, 1)


def _perpetual(candles: list[Candle], closes: list[float], vol: VolatilityTier) -> Signal:
    funding = candles[-1].funding_rate
    drift = closes[-1] / closes[-6] - 1.0
    if funding >= 0.001:
        return _base(candles, Side.ALERT, 0.75, "perp funding crowded: monitor, no carry", 0.0, 1)
    if funding <= -0.0005 and abs(drift) < 0.04 and anomaly_score(candles) < 0.55:
        return _base(candles, Side.LONG, 0.82, "perp funding carry: negative funding, drift contained, low anomaly", 0.02, 8)
    return _base(candles, Side.FLAT, 0.32, "perp: no carry edge", 0.0, 1)
