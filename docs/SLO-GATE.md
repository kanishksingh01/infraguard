# InfraGuard P1: read-only SLO evaluation

## Design
The gate reads Prometheus' query API and produces a deterministic verdict: `PASS`, `HOLD`, or `ABORT_RECOMMENDED`. It does **not** mutate a cluster.

```text
Prometheus instant-vector queries → numeric validation → threshold streaks
                                      ↓
                           PASS / HOLD / ABORT_RECOMMENDED
                                      ↓
                             JSON decision evidence
```

## Usage
```bash
python3 -m guard.cli --prometheus http://127.0.0.1:9090 --policy examples/policy.json --samples 3 --interval 10
```

- Exit 0: all thresholds passed in the final sample.
- Exit 2: consecutive breaches met an abort recommendation threshold.
- Exit 3: insufficient or missing data, or a breach has not yet persisted long enough.
- A failing or ambiguous Prometheus query yields HOLD, never PASS.
- Multi-series Prometheus responses are rejected as ambiguous. Policies should aggregate to exactly one series.

## Limitations
The evaluation CLI currently has no Kubernetes watch, Argo Rollouts integration, service discovery, authentication provider integration, or automatic remediation. Production readiness requires scoped data sources, stronger query security controls, and audit persistence. P2 adds verified policy-controlled actions only after observing real Kubernetes state.

## Safety
Limit Prometheus access to a trusted server. Do not pass attacker-controlled URLs or queries. No secrets, tokens or cloud credentials are required in this read-only prototype.
