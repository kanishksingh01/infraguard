# Guarded Argo Rollouts abort — experimental Kind-only

This implementation is deliberately constrained to `kind-infraguard` and `infraguard-lab`. It does not support changing cluster or namespace via command-line options. It must NOT be used on shared or production clusters.

## Policy
- Require two freshly evaluated Prometheus SLO breaches.
- Rollout must be a progressing/paused Argo Rollout with a fully observed generation.
- Re-read the rollout immediately before applying an abort status patch.
- Require an explicit `--execute` flag and a target-specific confirmation.
- Use Kubernetes JSON Patch atomic `test` operations against UID and resourceVersion before setting `/status/abort=true`.
- Error or conflict returns failure and never silently retries.
- Default operation is advisory; without `--execute`, no write is attempted.
- Kubernetes RBAC must independently restrict the actor to the lab namespace and `rollouts/status` only.

## Example (only after installing Argo Rollouts CRDs/controller in disposable Kind)

```bash
python -m guard.remediation --rollout checkout --prometheus http://127.0.0.1:9090
# Explicit lab-only authorization:
python -m guard.remediation --rollout checkout --prometheus http://127.0.0.1:9090 \
  --execute --confirm ABORT:infraguard-lab/checkout
```

This code has unit tests for the safety boundary but has **not yet** been validated against a real Argo Rollouts controller. Do not equate the mock tests to a successful live abort.

## Known limitations to resolve before any broader use
The read-only observer uses the invoking kubeconfig context, while remediation always patches the disposable Kind context. A future version must bind both reads and writes to one authenticated, namespace-scoped identity. The CLI uses current telemetry but does not yet enforce maximum time between evaluation and patch. The status-subresource JSON Patch behavior must be tested against the pinned Argo Rollouts version.
