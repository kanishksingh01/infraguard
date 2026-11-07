# Engineering case study — InfraGuard

## Problem
A deployment can pass pod readiness while dramatically increasing downstream work. A single faulty change can saturate shared backend capacity and degrade client-facing availability.

## Approach
I built an independent laboratory analogue: a Kubernetes-hosted HTTP gateway with configurable 1×–8× backend fanout, bounded backend concurrency, Prometheus telemetry, deterministic consecutive-breach SLO rules, real Argo Rollouts observation and an explicit, lab-only guarded abort. A read-only monitor also runs inside Kubernetes using a minimally scoped ServiceAccount.

## Reproducible evidence
- One Kind trial: baseline 40/40 successful requests; synthetic fanout fault 1/40 successful, with 271 rejected backend attempts; after a manual reset, 8/8 successful requests.
- Real Prometheus/Argo test: error ratio ~97.32% and ~162.26 backend rejections/second; SLO decision `ABORT_RECOMMENDED`; Argo controller observed the new canary as `Degraded` after guarded abort.
- A later Kind workflow repeated synthetic fault/reset trials three times and saved an aggregate report.
- The abort uses UID/resourceVersion checks, explicit approval, preflight/fsynced lab audit and namespace-scoped status-patch permissions.

**Proof:** [Kind benchmark](https://github.com/kanishksingh01/infraguard/actions/runs/42423455935) · [Prometheus/Argo integration](https://github.com/kanishksingh01/infraguard/actions/runs/42424865878).

## Stronger end-to-end evidence
[Coupled real canary, Prometheus, guarded abort and service recovery](https://github.com/kanishksingh01/infraguard/actions/runs/42425398415): 24/24 stable baseline requests succeeded; 754 of 800 requests to the bad canary failed; Prometheus measured 93.75% canary errors; after guarded abort the stable Service passed 24/24. Abort-to-stable verification: 34.36 seconds in a synthetic Kind run, not production MTTR.

## Engineering decisions
- Missing metrics produce HOLD, not PASS.
- A single spike does not trigger an abort: consecutive breaches are required.
- Rollout status must observe the current generation and match the expected UID.
- Remediation is disabled by default; no production context is selectable.
- In-cluster monitoring uses a ServiceAccount GET permission and never patches workloads.

## Important limitations
The original Argo exercise used unrelated lab metrics. A newer, stronger coupled-canary experiment now injects the failure into the real canary Pod and verifies stable-Service recovery after abort (24/24 successful requests) in the same test. That still does not establish production-level recovery reliability. The backend capacity model is in-process, not real TCP connection exhaustion. No production traffic, OpenAI infrastructure or employer configuration is involved.

## What would make this complete
Repeat the coupled recovery experiment across varied loads, add durable tamper-resistant audit and reconciliation leadership, and benchmark against native Argo analysis. See [release gates](RELEASE-STATUS.md) and [full walkthrough](END-TO-END.md).
