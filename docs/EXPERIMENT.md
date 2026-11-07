# P0 experiment protocol

## Run
`python3 -m lab.experiment --requests 120 --concurrency 12 --capacity 8 --output experiment-report.json`

## Design
1. Start fresh isolated local lab server on a loopback random port.
2. Issue 120 gateway requests with 12 concurrent clients and fanout=1.
3. Switch to fanout=8 and repeat with the same client/request settings.
4. Write p50, p95, p99, error ratio, backend attempt amplification and rejection counts.
5. Repeat the experiment multiple times; compare medians across runs.

## Hypothesis
Increased backend amplification increases contention for shared concurrency capacity, elevating failure rate or latency. No result is assumed beforehand. No production network connections are created beyond loopback.

## Caveats
Only local in-process concurrency limiting is modeled. Real production failures also involve TCP, shared caches, service mesh behavior and resource limits. The lab is a controlled analogue.
