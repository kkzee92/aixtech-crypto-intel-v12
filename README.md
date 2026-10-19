# AIxTech crypto intel v0.12: paper-only trading information system

Further advanced research harness for automated cryptocurrency **information** and paper strategy evaluation.
Builds on [kkzee92/aixtech-crypto-intel-v11](https://github.com/kkzee92/aixtech-crypto-intel-v11), prior versions, and the original [zeekiankok92/aixtech-crypto-intel](https://github.com/zeekiankok92/aixtech-crypto-intel).

It does not place live orders, does not store exchange secrets, and is not financial advice.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![version](https://img.shields.io/badge/version-0.12.0-blue)
![mode](https://img.shields.io/badge/execution-paper%20only-orange)
![Licence](https://img.shields.io/badge/licence-MIT-green)

## Enhancements in v0.12

- Multi-timeframe consistency proxies (short vs medium window alignment) for trend and breakout filters.
- Refined RSI divergence detection with price/RSI slope comparison.
- Simple historical VaR (95%) and CVaR proxies added to risk gate for dynamic size reduction.
- Expanded secret redaction: AWS AKIA/ASIA keys, GitHub PATs (ghp_), Slack tokens, more PEM/private key formats.
- Stronger zero-trust: input length limits, entropy checks on potential secrets, multi-hash integrity.
- Adaptive risk further reduced under high VaR or multi-timeframe mismatch.
- Updated docs.

See [docs/asset-class-strategies.md](docs/asset-class-strategies.md) and [docs/security-architecture.md](docs/security-architecture.md).

## What it does

- Eight asset classes with advanced multi-factor research rules incorporating multi-timeframe, divergence, StochRSI, cloud, OBV proxies.
- Multi-scale regime + volatility tier + anomaly scoring (z, skew, kurtosis) + VaR awareness.
- Signals with EMA, MACD, Bollinger, ADX, VWAP, StochRSI, cloud, OBV, divergence, multi-TF, then multi-gate risk with VaR.
- Paper-only backtests with class costs; enhanced hash-chained audit.
- Synthetic candles only. No network by default.

| Asset class | Enhanced research rule (v0.12) | Risk cap (base) | Cost |
|---|---|---|---|
| Major | Multi-EMA + MACD + Bollinger + ADX + VWAP + StochRSI + cloud + multi-TF + divergence; stand aside stress/high-vol/anomaly/VaR | 8% | 8 bps |
| Large-cap alt | Volume + multi-momentum + MACD + Bollinger + VWAP + StochRSI + multi-TF confirmation | 4% | 14 bps |
| Stablecoin | Adaptive peg + multi-stat (z, consecutive, skew, kurtosis) alerts only | 0% | n/a |
| DeFi | Calm multi-scale + channel + momentum + cloud + multi-TF + low anomaly | 2% | 22 bps |
| Meme | Qualified burst with volume profile, StochRSI not extreme, multi-TF consistency filters | 0.5% | 45 bps |
| L2 | Multi-period RS + relative volume + correlation + multi-TF consistency vs benchmark | 3% | 16 bps |
| RWA | Slow multi-scale low-vol trend with cloud, adaptive gap, momentum, anomaly, multi-TF | 2% | 12 bps |
| Perpetual | Funding carry with adaptive drift, stability, consistency, non-stress, low anomaly, VaR | 2% | 10 bps |

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python scripts/make_fixtures.py
PYTHONPATH=src python -m crypto_intel scan fixtures/candles_synthetic.json
PYTHONPATH=src python -m crypto_intel brief fixtures/candles_synthetic.json
PYTHONPATH=src python -m crypto_intel posture fixtures/candles_synthetic.json
```

## Controls

Paper-only. No live credentials. Class caps, adaptive confidence and sizing (VaR-aware), kill switch, drawdown, statistical anomaly + correlation + multi-TF + StochRSI gates, hash-chained audit, expanded redaction (AWS/GitHub/etc.), PDPA tripwire, gitleaks. Zero-trust research design.

## Honesty

No live exchange connector. Scores describe synthetic fixtures. Not investment, legal, or compliance advice. Research only.
