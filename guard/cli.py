"""Evaluate defined SLO gates from Prometheus; print decisions only, never change Kubernetes."""
import argparse
import json
import sys
from guard.policy import Evaluator, Threshold
from guard.prometheus import fetch_scalar, PrometheusError

def load_thresholds(path: str) -> list[Threshold]:
    with open(path, encoding="utf-8") as file:
        document = json.load(file)
    return [Threshold(name=item["name"], query=item["query"],
                      maximum=float(item["maximum"]),
                      consecutive_breaches=int(item.get("consecutive_breaches", 2)))
            for item in document["thresholds"]]

def main():
    parser = argparse.ArgumentParser(description="Read-only InfraGuard Prometheus SLO gate")
    parser.add_argument("--prometheus", required=True)
    parser.add_argument("--policy", default="examples/policy.json")
    parser.add_argument("--samples", type=int, default=2)
    parser.add_argument("--interval", type=float, default=10)
    args = parser.parse_args()
    if args.samples < 1 or args.interval < 0:
        parser.error("samples must be positive and interval non-negative")
    try:
        thresholds = load_thresholds(args.policy)
        evaluator = Evaluator(thresholds)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(f"invalid policy: {exc}")
    import time
    decision = None
    for index in range(args.samples):
        if index:
            time.sleep(args.interval)
        samples = {}
        for threshold in thresholds:
            try:
                samples[threshold.name] = fetch_scalar(args.prometheus, threshold.query)
            except (PrometheusError, ValueError):
                samples[threshold.name] = None
        decision = evaluator.evaluate(samples)
        print(json.dumps({"evaluation": index + 1, **decision}), flush=True)
        if decision["decision"] == "ABORT_RECOMMENDED":
            break
    # Exit 2 for recommendation, 3 for insufficient observations. Neither executes an action.
    return 2 if decision["decision"] == "ABORT_RECOMMENDED" else 3 if decision["decision"] == "HOLD" else 0

if __name__ == "__main__":
    sys.exit(main())
