# InfraGuard — End-to-end walkthrough

> **Status:** Laboratory prototype with live Kind, Prometheus, and Argo Rollouts CI coverage. Private portfolio project; independent of OpenAI.

## 1. The problem
A rollout can seem healthy at the pod level while dramatically increasing downstream calls. That extra fanout can saturate backend capacity, produce errors, and affect otherwise healthy clients. Standard readiness checks alone are not sufficient to assess the service-level impact.

**What we built:** A synthetic failure lab, metrics collection, deterministic SLO rules, read-only Argo Rollouts observation, and an **explicitly approved, lab-only abort**. AI is postponed.

## 2. The whole system at a glance

```text
  Load generator ──HTTP──> Fault lab (Deployment + ClusterIP Service)
                                  |
                     fanout 1 -> 8 (test-only switch)
                                  |
                       bounded simulated backend
                                  |
                    HTTP failures + rejection counters
                                  |
                         Prometheus scrape
                                  |
                      PromQL SLO evaluation
                                  |
      real Argo Rollout state ---> decision engine
                                  |
                  PASS | HOLD | ABORT_RECOMMENDED
                                  |
             lab-only explicit approval + CAS checks
                                  |
                  Argo Rollout status abort patch
                                  |
                       controller marks Degraded
```

*CAS = compare-and-swap-style preconditions using Kubernetes UID and resourceVersion.*

## 3. Follow a complete failure scenario

1. **Healthy baseline.** The gateway performs one backend attempt per request, under a concurrency limit. The load generator records successful requests, HTTP failures, and latency percentiles.
2. **Trigger regression.** A test-only switch increases backend fanout from 1 to 8. It models a shared *in-process* capacity bottleneck, **not** genuine TCP exhaustion.
3. **Measure the failure.** Requests compete for the same bounded backend pool; attempts are rejected and some gateway requests fail. Prometheus scrapes counters from the Kubernetes-hosted lab.
4. **Make a decision.** The evaluator checks aggregated PromQL thresholds and requires consecutive violations. Absent, ambiguous, or invalid metrics produce `HOLD`; they never authorize a healthy/pass decision.
5. **Correlate rollout state.** A read-only observer fetches a named real Argo Rollout. An old observedGeneration or non-active phase blocks an abort recommendation.
6. **Guarded intervention.** In disposable `kind-infraguard/infraguard-lab` only, the test explicitly permits a JSON Patch that tests the Rollout's UID and resourceVersion before requesting an abort. Default CLI mode is read-only.
7. **Verify.** The CI integration observes the Argo controller mark the target rollout `Degraded`. A separate P0 test resets the synthetic fault and confirms subsequent requests succeed. **These are different tests**; the Argo abort test does not itself prove application-level recovery.

## 4. How to reproduce (optional; CI runs automatically)

**No local setup is required to review progress.** Check the GitHub Actions workflows for live, disposable test runs:
- [Python/unit/Docker CI](../.github/workflows/ci.yml)
- [Real Kind workload and reset verification](../.github/workflows/kind-integration.yml)
- [Real Argo Rollouts + Prometheus SLO integration](../.github/workflows/argo-integration.yml)

For a code-only local demonstration, from the repo root with Python 3.10+:

```bash
python3 -m unittest discover -s tests -v
python3 -m lab.experiment --requests 120 --concurrency 12 --output experiment-report.json
```

The Kind workflow provisions and deletes a disposable cluster. The Argo workflow installs pinned Argo Rollouts v1.10.2 and tests the full synthetic-traffic → real Prometheus → SLO → guarded abort sequence.

## 5. Evidence and what it means

In one successful **Kind synthetic fault** run, baseline requests were 40/40 successful, faulty requests were 1/40 successful, and post-reset requests were 8/8 successful. The run recorded 320 backend attempts and 271 rejected attempts in the faulty phase. These results are lab-specific, not production performance claims. [Benchmark workflow run](https://github.com/kanishksingh01/infraguard/actions/runs/42397915441).

In a separate successful **Argo/Prometheus** run, Prometheus measured a simulated-workload error ratio of ~0.973 and backend rejections ~162.26/s. The policy recommended abort, a Kind-limited patch succeeded, and the Argo Rollout became `Degraded`. [End-to-end workflow run](https://github.com/kanishksingh01/infraguard/actions/runs/42398095089).

The repository's `docs/BENCHMARK.md` distinguishes a manual reset verification duration from autonomous MTTR. We have **not** measured automatic application-level recovery or statistically robust confidence intervals yet.

## 6. Where the code lives

| Component | Location | Purpose |
| --- | --- | --- |
| Fault injection | [lab/server.py](../lab/server.py) | Synthetic backend fanout, counters, HTTP endpoints |
| Traffic generator | [lab/load_test.py](../lab/load_test.py) | Requests, successes, p50/p95/p99 |
| Prometheus evaluation | [guard/prometheus.py](../guard/prometheus.py), [guard/policy.py](../guard/policy.py) | Metric collection and rule-based decision |
| Rollout observer | [guard/kubernetes.py](../guard/kubernetes.py), [guard/observe.py](../guard/observe.py) | Read-only state and SLO correlation |
| Guarded abort | [guard/remediation.py](../guard/remediation.py) | Explicit lab-only abort with version/identity checks |
| Kubernetes manifests | [deploy/](../deploy/) | Kind, lab, Prometheus, Argo canary and reference RBAC |
| Real integration test | [lab/argo_metrics_smoke.py](../lab/argo_metrics_smoke.py) | End-to-end test orchestrator |

## 7. What is NOT done

- No production-grade reconciliation controller or Kubernetes watch loop yet.
- No audit storage, robust SLO rollout policy configuration, or production authorization model.
- The lab-only abort test uses a privileged disposable Kind identity; reference least-privilege RBAC is **not yet exercised** by that integration.
- No proven application-level automatic recovery, rollout safety under real shared backend failures, or validated operating SLO.
- No AI-assisted RCA yet.

## 8. Roadmap and hiring demonstration

- **Next:** Measure repeatable recovery and distinguish abort from restored availability; exercise least-privilege ServiceAccount controls.
- **Then:** Harden the controller, audit actions, run negative tests, compare native Argo analysis and our gate.
- **Later:** AI-assisted incident explanation with evidence, never as an unguarded mutation path.

The portfolio case study should show the failure, concrete telemetry, the exact defensive decision, and tests that prove both success and safe refusal. See [P0 issue](https://github.com/kanishksingh01/infraguard/issues/1) and [engineering blueprint](https://github.com/kanishksingh01/infraguard/issues/6).
