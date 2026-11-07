# InfraGuard P0 architecture

## Scope
This P0 code is a **local simulator**, not yet a Kubernetes controller.

- `/request`: gateway endpoint; configured parallel fanout to a bounded in-process backend.
- `/metrics`: JSON metrics and counters; a Prometheus exporter is P1 work.
- `POST /admin/fanout?value=1..8`: test-only fault toggle.
- `lab/load_test.py`: concurrent synthetic traffic and latency/error summary.

The bounded backend pool models a shared connection pool. Exhaustion rejects backend work, propagating failures to gateway requests. It does **not** simulate real TCP socket exhaustion or reproduce any private production incident.

## P1 target

```text
Kubernetes events / Argo Rollouts state
                  + Prometheus HTTP API
                           |
                   Signal evaluator
                           |
                  Deterministic policy
                           |
                   Dry-run decision
                           |
           [P2] approved rollout intervention
```

## Operational safety
The simulator only listens on 127.0.0.1. Never expose the unauthenticated fault-toggle endpoint. No real cloud credentials or company infrastructure are required.

## Measurement caveats
Compare multiple independent runs and record host hardware, concurrency and software versions; p99 on tiny samples is noisy. This is a lab approximation, not proof of production efficacy.
