# InfraGuard continuous SLO observation

`python -m guard.monitor` is a read-only polling monitor. It retains the policy evaluator's consecutive-breach state between observations, correlates each sample with a live named Argo Rollout, and emits timestamped JSON decisions. It **does not execute an abort**, even when the decision is ABORT_RECOMMENDED.

Example in an isolated lab with Prometheus and Argo Rollouts:

```bash
python -m guard.monitor --context kind-infraguard \
  --namespace infraguard-lab --rollout checkout \
  --prometheus http://127.0.0.1:9090 \
  --policy examples/lab-policy.json --iterations 3 --interval 10
```

`--iterations 0` means a continuous read-only process until interrupted. This is **not** a controller-runtime reconciliation manager, a Kubernetes operator with leader election, or a deployment-safe autonomous remediator. Missing/invalid Prometheus metrics return HOLD rather than PASS. It relies on the invoking kubeconfig identity and must be scoped to nonproduction resources.
