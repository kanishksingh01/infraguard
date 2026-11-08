# InfraGuard

**Kubernetes rollout safety with evidence-based SLO gates and lab-only guarded aborts.** Independent cloud reliability engineering project; not affiliated with OpenAI. Repository remains private during development.

**Engineering case study:** [Problem, design, measured evidence and tradeoffs](docs/CASE-STUDY.md).

**Start:** [Full end-to-end guide](docs/END-TO-END.md) · [Release criteria](docs/RELEASE-STATUS.md).

InfraGuard models backend call amplification, measures its impact with Prometheus and combines consecutive SLO breaches with real Argo Rollouts state. The opt-in abort is restricted to disposable Kind and protected by UID/resourceVersion checks, namespaced RBAC and a local audit record. It has automated unit, Kind and Argo integration workflows.

**Coupled recovery evidence:** [real canary fault → Prometheus SLO → guarded abort → stable Service 24/24 recovered](https://github.com/kanishksingh01/infraguard/actions/runs/42425398415) in disposable Kind; 34.36 s abort-to-verification in one synthetic trial.


**Repeatable recovery:** [Three load levels (4/6/8) with 3/3 successful aborts and stable-service recoveries](https://github.com/kanishksingh01/infraguard/actions/runs/42427979374). Median abort-to-verification 34.418 s (synthetic Kind).

**Current status:** Working, CI-tested experimental prototype; not a production controller. The coupled canary recovery lab passed; broader production-grade recovery and hardening remain unproven. AI features deferred.

[CI](.github/workflows/ci.yml) · [Kind benchmark](.github/workflows/kind-integration.yml) · [Argo SLO/abort](.github/workflows/argo-integration.yml) · [Architecture](docs/ARCHITECTURE.md)
