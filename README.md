# InfraGuard

**Kubernetes rollout safety with evidence-based SLO gates and lab-only guarded aborts.** Independent cloud reliability engineering project; not affiliated with OpenAI. Repository remains private during development.

**Engineering case study:** [Problem, design, measured evidence and tradeoffs](docs/CASE-STUDY.md).\n\n**Start:** [Full end-to-end guide](docs/END-TO-END.md) · [Release criteria](docs/RELEASE-STATUS.md).

InfraGuard models backend call amplification, measures its impact with Prometheus and combines consecutive SLO breaches with real Argo Rollouts state. The opt-in abort is restricted to disposable Kind and protected by UID/resourceVersion checks, namespaced RBAC and a local audit record. It has automated unit, Kind and Argo integration workflows.

**Current status:** Working, CI-tested experimental prototype; not a production controller. Application-level recovery following abort remains unproven. AI features deferred.

[CI](.github/workflows/ci.yml) · [Kind benchmark](.github/workflows/kind-integration.yml) · [Argo SLO/abort](.github/workflows/argo-integration.yml) · [Architecture](docs/ARCHITECTURE.md)
