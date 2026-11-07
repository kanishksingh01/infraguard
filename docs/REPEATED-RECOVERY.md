# Independent repeated recovery trials

The `Repeated Canary Recovery Evidence` GitHub workflow creates **three separate disposable Kind clusters on distinct CI runners**. Each reproduces the same synthetic canary failure, observes real Prometheus SLO breaches, and performs the explicitly approved Kind-only Argo abort. It saves a per-trial JSON report and audit log.

The aggregator **fails** if any trial lacks baseline success, has failed requests after the stable-Service verification, lacks a guarded abort, or does not reproduce faulty traffic. It reports median/min/max of abort-to-stable-Service-probe verification and faulty-canary error ratio, without pretending that three experiments prove production availability or statistical confidence.

This workflow uses more CI runner time than a unit test; it runs on explicit workflow changes and can be run manually. It is not a periodic background job.
