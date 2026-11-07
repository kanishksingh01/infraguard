"""Aggregate independent coupled-canary Kind trials; reject missing recovery proof."""
import argparse
import json
import math
import statistics
from pathlib import Path

def as_number(value, key):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key}: expected numeric measurement")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{key}: invalid numeric measurement")
    return float(value)

def aggregate(reports):
    if len(reports) < 3:
        raise ValueError("at least three independent coupled-canary reports are required")
    recovery = []
    fault_ratios = []
    faulty_attempts = 0
    for index, r in enumerate(reports, 1):
        if not isinstance(r, dict):
            raise ValueError(f"trial {index}: expected report object")
        for field in ("baseline_service", "service_after_abort"):
            part = r.get(field)
            if not isinstance(part, dict) or part.get("failed") != 0:
                raise ValueError(f"trial {index}: {field} did not show complete availability")
            if as_number(part.get("requests"), field+".requests") < 1:
                raise ValueError(f"trial {index}: no requests in {field}")
        if r.get("slo_decision") != "ABORT_RECOMMENDED":
            raise ValueError(f"trial {index}: SLO gate never requested an abort")
        action = r.get("guarded_abort")
        if not isinstance(action, dict) or action.get("action_executed") is not True:
            raise ValueError(f"trial {index}: no verified abort")
        fault = as_number(r.get("faulty_canary_failed_requests"), "faulty_canary_failed_requests")
        good = as_number(r.get("faulty_canary_successful_requests"), "faulty_canary_successful_requests")
        if fault <= 0 or fault + good == 0:
            raise ValueError(f"trial {index}: no observable fault")
        recovery.append(as_number(
            r.get("abort_to_stable_service_verification_seconds"),
            "abort_to_stable_service_verification_seconds"))
        fault_ratios.append(fault/(fault+good))
        faulty_attempts += int(fault+good)
    return {
        "trials": len(reports),
        "scope": "independent synthetic Kind canary trials, not a production SLO or MTTR",
        "verified_abort_and_service_recovery_in_every_trial": True,
        "abort_to_stable_verification_seconds": {
            "median": round(statistics.median(recovery), 3),
            "min": round(min(recovery), 3),
            "max": round(max(recovery), 3),
        },
        "faulty_canary_error_ratio": {
            "median": round(statistics.median(fault_ratios), 4),
            "min": round(min(fault_ratios), 4),
            "max": round(max(fault_ratios), 4),
        },
        "synthetic_requests_during_fault_total": faulty_attempts,
        "limitations": "three or more trials; runner noise, synthetic capacity and nonproduction controls",
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+")
    parser.add_argument("--output", default="coupled-repeatability-summary.json")
    args = parser.parse_args()
    result = aggregate([json.loads(Path(path).read_text(encoding="utf-8"))
                        for path in args.reports])
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
