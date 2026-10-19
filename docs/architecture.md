# Architecture (v0.12)

```mermaid
flowchart LR
    FX[\"fixtures/candles_synthetic.json\"] --> M[\"market.py / regime.py\"]
    M --> RG[\"regime.py multi-scale + vol tier + anomaly + multi-TF\"]
    M --> ST[\"strategies.py multi-factor + multi-TF + divergence per asset class\"]
    RG --> ST
    ST --> RK[\"risk.py VaR-aware gates\"]
    CS[\"costs.py\"] --> EN[\"engine.py paper fill\"]
    RK --> EN
    EN --> AU[\"security.py audit chain + expanded redaction\"]
    PS[\"posture.py attestation and RBAC\"] --> CLI[\"cli.py\"]
    EN --> CLI
```

Runtime dependencies: Python standard library. Tests inject fetchers; no network by default.
See security-architecture.md and asset-class-strategies.md.
