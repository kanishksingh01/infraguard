# InfraGuard — Community outreach kit (draft, not posted)

**Target communities:** [Argo Rollouts GitHub Discussions](https://github.com/argoproj/argo-rollouts/discussions), [CNCF/Argo Slack #argo-rollouts](https://argoproj.github.io/community/join-slack/), [CNCF TAG Operational Resilience](https://contribute.cncf.io/community/tags/operational-resilience/).

**Discussion type:** Argo Rollouts "Show and tell" only if category is open and project is accessible; otherwise a substantive design question in "General", not a bug report.

## Draft title
Canary rollback evidence: is a separate sustained-Prometheus gate useful alongside native Argo AnalysisTemplates?

## Draft
I'm experimenting with an independent Kubernetes rollout-safety lab called InfraGuard. I built a disposable Kind scenario in which a new canary amplifies backend calls, Prometheus observes the resulting errors, and a bounded deterministic SLO reconciler requests an explicitly approved Argo Rollouts abort.

A small repeatability experiment passed 3/3 independent synthetic trials at client concurrencies 4/6/8. Median time from abort request to verified healthy stable-Service probes was 34.35s (range 33.754–34.937s). This is a **Kind lab metric**, not production MTTR or a claim to outperform Argo.

I'd especially value maintainers' feedback on two questions: (1) when is a separate SLO gate justified instead of using native AnalysisTemplates? (2) what safety and audit requirements would you expect before trusting an external controller to request an abort?

If a focused lab comparison or short community-meeting presentation would be useful, I'm happy to share the design and negative/failure cases. The code is still private while I finish the public-safe release.

## Conversation follow-up
If someone responds, provide a minimal sanitised decision policy, error timeseries and test reproduction; ask whether an existing Argo extension or project would be a better fit. Do not ask maintainers to review an inaccessible repository.

## References
- [Argo Rollouts community Discussions](https://github.com/argoproj/argo-rollouts/discussions)
- [Argo Slack participation](https://argoproj.github.io/community/join-slack/)
- [Internal lab end-to-end documentation](END-TO-END.md) and [release status](RELEASE-STATUS.md)

**Before posting:** Publish a public-safe runnable reproduction or read-only case-study page, get permission before sharing any employer-related examples, and avoid claiming Argo bugs or production improvement without proof.
