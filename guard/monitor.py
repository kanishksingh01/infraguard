"""Persistent read-only rollout/SLO monitor.

The monitor holds consecutive-breach state across polling iterations and never
executes or authorizes a Kubernetes mutation. No automatic rollback is possible.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from guard.cli import load_thresholds
from guard.policy import Evaluator
from guard.prometheus import fetch_scalar, PrometheusError
from guard.kubernetes import get_rollout, KubernetesError, combine_rollout_and_slo
from guard.kubeclient import get_rollout_incluster

def monitor(namespace, name, prometheus, policy, *, iterations=3, interval=10,
            context=None, in_cluster=False, sleeper=time.sleep):
    if not isinstance(iterations, int) or iterations < 0 or interval < 0:
        raise ValueError("iterations must be nonnegative and interval nonnegative")
    if not in_cluster and not context:
        raise ValueError("explicit Kubernetes context is required")
    thresholds = load_thresholds(policy)
    evaluator = Evaluator(thresholds)
    index = 0
    while iterations == 0 or index < iterations:
        if index:
            sleeper(interval)
        index += 1
        try:
            state = (get_rollout_incluster(namespace, name) if in_cluster
                     else get_rollout(namespace, name, context=context))
        except KubernetesError:
            state = None
        samples = {}
        for threshold in thresholds:
            try:
                samples[threshold.name] = fetch_scalar(prometheus, threshold.query)
            except (PrometheusError, ValueError):
                samples[threshold.name] = None
        slo = evaluator.evaluate(samples)
        decision = combine_rollout_and_slo(state, slo)
        decision["observed_at_utc"] = datetime.now(timezone.utc).isoformat()
        decision["iteration"] = index
        decision["execution_mode"] = "observe_only"
        decision["action_executed"] = False
        yield decision

def main():
    parser = argparse.ArgumentParser(description="Continuous read-only InfraGuard SLO monitor")
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--rollout", required=True)
    parser.add_argument("--context", help="Explicit kubeconfig context for external mode")
    parser.add_argument("--in-cluster", action="store_true", help="Use Kubernetes ServiceAccount API credentials")
    parser.add_argument("--prometheus", required=True)
    parser.add_argument("--policy", default="examples/lab-policy.json")
    parser.add_argument("--iterations", type=int, default=3,
                        help="Number of observations (0 means continuous until interrupted)")
    parser.add_argument("--interval", type=float, default=10)
    args = parser.parse_args()
    try:
        for decision in monitor(args.namespace, args.rollout, args.prometheus,
                                args.policy, iterations=args.iterations,
                                interval=args.interval, context=args.context,
                                in_cluster=args.in_cluster):
            print(json.dumps(decision), flush=True)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"error": str(exc), "action_executed": False}), file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
