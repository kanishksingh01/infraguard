"""Observe a named Rollout and current SLO evidence. Never mutates Kubernetes."""
import argparse
import json
import sys
import time
from guard.cli import load_thresholds
from guard.policy import Evaluator
from guard.prometheus import fetch_scalar, PrometheusError
from guard.kubernetes import get_rollout, KubernetesError, combine_rollout_and_slo

def observe(namespace, rollout_name, prometheus, policy, samples=2, interval=10, kubectl="kubectl", context=None):
    if samples < 1 or interval < 0:
        raise ValueError("samples must be >= 1 and interval non-negative")
    thresholds = load_thresholds(policy)
    evaluator = Evaluator(thresholds)
    result = None
    for index in range(samples):
        if index:
            time.sleep(interval)
        try:
            state = get_rollout(namespace, rollout_name, kubectl=kubectl, context=context)
        except KubernetesError:
            state = None
        measurements = {}
        for threshold in thresholds:
            try:
                measurements[threshold.name] = fetch_scalar(prometheus, threshold.query)
            except (PrometheusError, ValueError):
                measurements[threshold.name] = None
        slo = evaluator.evaluate(measurements)
        result = combine_rollout_and_slo(state, slo)
        result["evaluation"] = index + 1
        print(json.dumps(result), flush=True)
        if result["decision"] == "ABORT_RECOMMENDED":
            break
    return result

def main():
    parser = argparse.ArgumentParser(description="Read-only Argo Rollout and SLO gate")
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--rollout", required=True)
    parser.add_argument("--context", help="Explicit kubeconfig context (recommended)")
    parser.add_argument("--prometheus", required=True)
    parser.add_argument("--policy", default="examples/policy.json")
    parser.add_argument("--samples", type=int, default=2)
    parser.add_argument("--interval", type=float, default=10)
    args = parser.parse_args()
    try:
        result = observe(args.namespace, args.rollout, args.prometheus,
                         args.policy, args.samples, args.interval, context=args.context)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    return {"PASS": 0, "ABORT_RECOMMENDED": 2, "HOLD": 3}[result["decision"]]

if __name__ == "__main__":
    sys.exit(main())
