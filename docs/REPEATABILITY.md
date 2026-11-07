# Repeated Kind synthetic fault benchmark

The `Kind Integration` workflow runs **three consecutive trials** of the same synthetic service fanout failure in one disposable Kubernetes cluster, writing individual JSON reports and a summary artifact.

Each trial requires:
- No failed baseline requests.
- At least one failed request under synthetic fanout saturation.
- Zero failed requests after the manually issued reset.

The summary includes median error ratios, minimum and maximum faulty error ratio, summed backend rejections, and median time to issue reset plus probe. These are intentionally not called production MTTR, rollback efficacy, or statistical confidence intervals. Three trials are only a smoke-level repeatability check; robust benchmarking still requires larger samples, repetitions under distinct load/hosts, and a true bad-canary to healthy-service recovery comparison.
