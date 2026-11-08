# InfraGuard — Release status and evidence

## Lab-V1 acceptance
- [x] Reproducible synthetic connection-amplification failure inside disposable Kubernetes
- [x] Real Prometheus scrape, deterministic consecutive-breach SLO evaluation and bounded polling reconciler
- [x] Read-only Argo canary state and UID/resourceVersion-guarded, approval-gated abort
- [x] Audit preflight and namespace-scoped, lab-only remediator identity tests
- [x] Application-level stable-Service probes after the failed canary is aborted
- [x] Three **independent Kind trials** with all aborts and post-abort Service checks passing
- [x] Varied-load 4/6/8-concurrency repeatability workflow: 3/3 independent Kind recovery trials passed

## Observed evidence
[Three-trial recovery workflow](https://github.com/kanishksingh01/infraguard/actions/runs/42426511514) passed. Abort-to-stable-Service verification: median 36.767 seconds, range 36.608–37.216 seconds. Faulty canary error ratio: median 92.71%. This is a small synthetic experiment, **not production MTTR**. [Varied-load three-trial workflow](https://github.com/kanishksingh01/infraguard/actions/runs/42427979374) also passed: median abort-to-stable verification 34.418 s (34.362–36.691 s), median faulty-canary error ratio 97.09%, over 3,072 synthetic requests across concurrency levels 4, 6, 8. See `docs/VARIED-LOAD-BENCHMARK.md`.

## Non-goals for a lab V1
No changes to external or employer clusters; no real production rollback; no certified reliability SLO; no AI-driven mutation. Lab test artifacts are not immutable audit infrastructure.

## Remaining before production consideration
A production Kubernetes native controller/watch loop (a bounded lab polling reconciler now exists), durable/secured audit service, authorization and credentials against threat models, native Argo AnalysisTemplate comparator, independently repeated larger-scale benchmarks, and operator-grade deployment guidance.

**Classification: reproducible experimental Kubernetes rollout guard; not production-ready.** [Walkthrough](END-TO-END.md).
