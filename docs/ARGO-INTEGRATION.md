# End-to-end Argo Rollouts CI

The workflow installs Argo Rollouts v1.10.2 into disposable Kind, deploys a canary, waits for a pause, observes the real Rollout, evaluates two consecutive synthetic SLO breaches via a local Prometheus-compatible test server, then applies a guarded abort and verifies the Rollout state.

**Real:** Kubernetes, Argo Rollouts, kube API observation, status-subresource patch and controller reconciliation.

**Synthetic:** Prometheus metric samples (0.20 for the test-defined metrics); these represent deterministic test inputs, not incident data or measurements from traffic.

The experimental abort uses explicit approval, a pinned Kind context and UID/resourceVersion preconditions. See `deploy/remediation-rbac.yaml` for a proposed namespace-scoped ServiceAccount. The workflow currently uses its disposable Kind context, not that ServiceAccount.

This is NOT evidence of production safety, full Prometheus telemetry, or production rollback performance. Future tests must join real traffic-derived metrics with the Argo recovery path and verify least-privilege identities.
