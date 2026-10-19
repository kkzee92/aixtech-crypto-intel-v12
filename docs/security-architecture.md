# Security architecture (v0.12 enhanced)

Version 0.12 expands multi-timeframe filters, VaR gates, broader secret patterns (AWS AKIA, GitHub ghp_, Slack xoxb, more PEM), entropy proxies, input length limits, and refined zero-trust. Research design only; not certified, not legal advice.

## Trust boundaries

```mermaid
flowchart LR
    F[\"Synthetic fixture or injected public ticker\"] --> AT[\"Source attestation + multi-hash + statistical anomaly + multi-TF + VaR\"]
    AT --> S[\"Strategy rules + multi-scale regime + VWAP/Bollinger/ADX/cloud + adaptive + divergence\"]
    S --> R[\"Risk gate: class caps, kill switch, drawdown, adaptive size/confidence + anomaly/corr/VaR\"]
    R --> P[\"Paper fill only\"]
    P --> A[\"Hash-chained audit with enhanced sanitization and integrity tags\"]
    K[\"Trade or withdrawal keys\"] -.-> X[\"Refused. Never loaded\"]
    RBAC[\"Researcher, auditor, operator\"] --> R
```

No order router. Paper-only enforced. Zero-trust: every input attested, scored, sanitized, length-limited.

## Roles

Unchanged: Researcher / Auditor / Operator. No trader role. Broker is separate.

## Data classes and handling

Expanded redaction for AWS keys, GitHub PATs, Slack tokens, additional private key formats, seed proxies. Wallet, personal data, trade keys refused or redacted. Source must be SYNTHETIC or PUBLIC_READ with checksums. Inputs limited in length.

## Feed integrity and anomaly

Enhanced anomaly_score includes return z-score, volume z-score, consecutive anomalies, skewness, kurtosis proxy, multi-bar consistency. High scores reduce size or block. Correlation and multi-TF checks for relative strategies. VaR proxy further gates size.

## Threats and controls

| Threat | Control |
|---|---|
| Secret committed | gitleaks + expanded redaction (AWS, GitHub PAT, Slack, PEM, JWT, base64, seeds) |
| Trade key pasted | refuse_trade_secret |
| Fixture injection | SYNTHETIC + multi-hash + attestation + anomaly + length limits |
| Stale/jumped/anomalous data | multi-stat anomaly + consistency + correlation + multi-TF + VaR gates |
| Oversized risk | class caps + adaptive floors + anomaly/VaR size reduction + dynamic vol sizing |
| Runaway loss | drawdown + kill switch + VaR |
| Audit tamper | SHA-256 chain + verify |
| Live mistake | mode guard, no client, RBAC, paper-only |
| Personal data / injection | tripwire + sanitization + length limits + entropy |
| Privilege creep | no order role |

## Incident handling

1. Engage kill switch.
2. Freeze audit; record attestation digests, high anomaly/VaR/correlation scores.
3. Rotate secrets externally; purge history.
4. No public issues containing secrets or personal data.
5. Human review before clearing kill switch.
6. Update patterns post-incident.

## Operating rules

- Read-only credentials only if ever added; never logged.
- All logs sanitized and length-checked.
- Default paper/research. Broker separate and human-approved.
- Zero-trust assumptions.
- Strategies and gates versioned with tests and human review.
- Adaptive risk reduces exposure under anomaly, VaR, or multi-TF mismatch.

Prioritizes research integrity and prevention of accidental live execution or data leakage.
