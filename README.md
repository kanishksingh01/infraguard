# InfraGuard

**Kubernetes rollout reliability and guarded failure recovery** · Independent portfolio project · Private during development

**Start here:** [Read the complete end-to-end walkthrough](docs/END-TO-END.md).

This walkthrough covers the problem, diagrams, actual deployment and observability flow, a simulated incident, test evidence, limitations, and the roadmap. GitHub Actions performs disposable Kubernetes integration tests; no local setup is required to review them.

**Verified:** Python CI, disposable Kind workload/metrics tests, and a real Argo Rollouts abort driven by Prometheus-scraped synthetic fault metrics. **Not yet:** production hardening or measured automatic service recovery.

[Unit and container CI](.github/workflows/ci.yml) · [Kind workflow](.github/workflows/kind-integration.yml) · [Argo/Prometheus workflow](.github/workflows/argo-integration.yml) · [Architecture](docs/ARCHITECTURE.md)

No production secrets, employer repositories, or company infrastructure are used. The lab-only mutation path is opt-in and is not intended for deployment outside disposable Kind.
