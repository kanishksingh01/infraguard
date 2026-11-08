# Varying load across independent canary trials

The three independent disposable Kind CI runs now use synthetic faulty-canary client concurrencies of **4, 6 and 8**, rather than repeating one load level three times. The aggregate validator rejects missing, duplicated, or unsupported load levels and rejects any trial without verified good baseline, faulty canary traffic, guarded abort and healthy post-abort Service.

It reports median/range across *different load intensities* and records each load level. Such a median is a descriptive cross-scenario metric, **not** a confidence interval for a fixed workload. The test remains a small synthetic benchmark, with Argo Rollouts v1.10.2 and no production connections.
