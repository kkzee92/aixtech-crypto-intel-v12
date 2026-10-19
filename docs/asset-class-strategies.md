# Asset-class strategy notes (v0.12)

These rules are research heuristics. Each class has an edge hypothesis, an entry, an invalidation, a horizon, and a size cap. They are not a promise of return. Version 0.12 adds multi-timeframe consistency proxies, refined RSI divergence, and VaR-aware risk.

Regime labels, from `regime.py`:

- **trend**: multi-bar move with ATR conditions
- **range**: neither stress nor trend
- **stress**: average bar range at least 3.5% of price; directional ideas stand aside

## Major

Hypothesis: liquid majors trend with multi-EMA, MACD, Bollinger, ADX, VWAP, cloud, StochRSI, multi-TF alignment, and divergence support unless stress, high-vol weak, high anomaly, or elevated VaR. Mean reversion only in range with washed-out StochRSI. Cap 8%. Horizon 8 or 20 bars. Research cost 8 bps round trip.

## Large-cap alt

Hypothesis: breakouts need volume, multi-momentum, MACD, Bollinger upper, VWAP, StochRSI, and multi-TF confirmation. Stress suppressed. Cap 4%. Cost 14 bps.

## Stablecoin

Hypothesis: the useful signal is a peg break with multi-stat (z, consecutive, skew, kurtosis). Deviation thresholds raise alerts. Risk gate forces size to zero. No order.

## DeFi

Hypothesis: trend signals only in multi-scale calm non-stress with channel, cloud, momentum, multi-TF, and low anomaly. Cap 2%. Cost 22 bps.

## Meme

Hypothesis: most bursts are untradeable. Qualified burst needs volume consistency, adaptive extension, StochRSI not extreme, multi-TF ok. Horizon 3 bars. Cap 0.5%. Cost 45 bps.

## L2

Hypothesis: L2 tokens are multi-period relative strength bets versus consistent non-stress benchmark with volume, correlation, and multi-TF. Cap 3%. Cost 16 bps.

## RWA

Hypothesis: tokenised real-world assets should be slow with cloud confirmation. Adaptive gap, stress, high vol, high anomaly, or multi-TF mismatch halt. Cap 2%, horizon 24 bars. Cost 12 bps.

## Perpetual

Hypothesis: negative funding with contained multi-bar drift, stability, consistency, non-stress, low anomaly, acceptable VaR is a carry observation. Crowded funding is alert. Cap 2%. Cost 10 bps. Does not model liquidation or exchange risk.

## Still out of scope

- Live order routing, withdrawal, and trade API keys.
- A broker adapter. That would be a separate human-approved system.
- Claims about future returns. Scores describe the synthetic fixture.
