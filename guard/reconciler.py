"""Bounded advisory SLO reconciler for disposable Kind, not a production operator."""
import argparse
import json
import subprocess
import sys
import time
from urllib.parse import urlparse
from guard.cli import load_thresholds
from guard.kubernetes import get_rollout, KubernetesError, combine_rollout_and_slo
from guard.policy import Evaluator
from guard.prometheus import fetch_scalar, PrometheusError
from guard.remediation import LAB_CONTEXT, LAB_NAMESPACE, abort_with_preconditions, RemediationError

def validate_loopback_context(runner=subprocess.run):
    cmd = ["kubectl", "config", "view", "--raw", "--minify",
           "--context", LAB_CONTEXT, "-o", "json"]
    try:
        result = runner(cmd, text=True, capture_output=True, timeout=8, check=False)
        if result.returncode:
            raise ValueError("unable to read Kind context")
        clusters = json.loads(result.stdout).get("clusters") or []
        if len(clusters) != 1:
            raise ValueError("ambiguous cluster")
        url = urlparse((clusters[0].get("cluster") or {}).get("server", ""))
        if url.scheme != "https" or url.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("API server is not loopback HTTPS")
        return url.hostname
    except (OSError, subprocess.TimeoutExpired, TypeError, ValueError) as exc:
        raise ValueError("unable to verify loopback Kind API server") from exc

class Reconciler:
    def __init__(self, rollout, prometheus, policy, *,
                 state_reader=get_rollout, metric_reader=fetch_scalar,
                 aborter=abort_with_preconditions, execute=False, approved=False,
                 audit_path="infraguard-controller-audit.jsonl"):
        self.rollout = rollout
        self.prometheus = prometheus
        self.thresholds = load_thresholds(policy)
        self.evaluator = Evaluator(self.thresholds)
        self.state_reader = state_reader
        self.metric_reader = metric_reader
        self.aborter = aborter
        self.execute = execute
        self.approved = approved
        self.audit_path = audit_path
        self.acted = False

    def step(self):
        try:
            state = self.state_reader(LAB_NAMESPACE, self.rollout, context=LAB_CONTEXT)
        except KubernetesError:
            state = None
        active = state is not None and not state.reconciling and state.phase in ("Paused", "Progressing")
        if active:
            readings = {}
            for threshold in self.thresholds:
                try:
                    readings[threshold.name] = self.metric_reader(
                        self.prometheus, threshold.query)
                except (PrometheusError, ValueError):
                    readings[threshold.name] = None
        else:
            # Never carry SLO failure streaks across missing/stale/finished Rollouts.
            self.evaluator.streaks = {t.name: 0 for t in self.thresholds}
            readings = {}
        result = combine_rollout_and_slo(state, self.evaluator.evaluate(readings))
        result["controller"] = "bounded-polling-prototype"
        if self.execute and result["decision"] == "ABORT_RECOMMENDED":
            if not self.approved:
                raise RemediationError("explicit approval required")
            if self.acted:
                raise RemediationError("duplicate abort forbidden")
            result["execution"] = self.aborter(
                self.rollout, result, approved=True, audit_path=self.audit_path)
            self.acted = True
        return result

def main():
    parser = argparse.ArgumentParser(description="Bounded Kind read-only rollout SLO reconciler")
    parser.add_argument("--rollout", required=True)
    parser.add_argument("--prometheus", required=True)
    parser.add_argument("--policy", default="examples/canary-policy.json")
    parser.add_argument("--cycles", type=int, default=12)
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--audit-file", default="infraguard-controller-audit.jsonl")
    args = parser.parse_args()
    if not 1 <= args.cycles <= 300 or not .1 <= args.interval <= 300:
        parser.error("cycles must be 1..300 and interval 0.1..300")
    approved = args.confirm == f"ABORT:{LAB_NAMESPACE}/{args.rollout}"
    if args.execute and not approved:
        parser.error("explicit lab target confirmation required")
    if args.execute:
        try:
            validate_loopback_context()
        except ValueError as exc:
            parser.error(str(exc))
    try:
        controller = Reconciler(args.rollout, args.prometheus, args.policy,
                                execute=args.execute, approved=approved,
                                audit_path=args.audit_file)
        for index in range(args.cycles):
            if index:
                time.sleep(args.interval)
            result = controller.step()
            print(json.dumps(result), flush=True)
            if controller.acted:
                break
    except (OSError, ValueError, RemediationError) as exc:
        print(json.dumps({"action_executed": False, "error": str(exc)}), file=sys.stderr)
        return 4
    return 0

if __name__ == "__main__":
    sys.exit(main())
