# Kubernetes/Argo Rollouts observation (P1)

## Scope and safety
This integration is **read-only**. It retrieves the named Argo Rollouts custom resource through `kubectl get ... -o json` and performs Prometheus queries. There is no rollback or cluster mutation path.

Example (lab environment with kubectl and Prometheus available):

```bash
python3 -m guard.observe \
  --namespace infraguard-lab \
  --rollout checkout \
  --prometheus http://127.0.0.1:9090 \
  --policy examples/policy.json \
  --samples 3 --interval 10
```

Exit codes: 0 PASS, 2 ABORT_RECOMMENDED, 3 HOLD. This is advisory only.

## Safety behavior
- Names validated before any kubectl invocation; subprocess never runs through a shell.
- Resource identity checked; stale `observedGeneration` forces HOLD.
- Healthy/Degraded/Unknown phase does not produce an abort suggestion.
- Missing or ambiguous Prometheus samples force HOLD.
- A sustained SLO regression can produce ABORT_RECOMMENDED only for a Progressing/Paused Rollout.
- No cluster changes are performed.
- Namespace-scoped RBAC sample is in `deploy/rbac.yaml`.

## Known limitations
- `kubectl` uses the invoking user's configured identity, not automatically the sample ServiceAccount. Use an isolated lab identity with the minimal Role above.
- The phase value is Argo Rollouts version-dependent; future work should parse rollout conditions and stable/canary replica sets more precisely.
- This is polling, not a resource watch.
- P2 must implement an explicit, audited authorization boundary before any rollout-changing action can be permitted.
