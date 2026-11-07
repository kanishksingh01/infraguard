"""Summarize repeated Kind synthetic fault runs without claiming production MTTR."""
import argparse
import json
import statistics
from pathlib import Path

def aggregate(documents):
    if len(documents) < 2:
        raise ValueError("at least two independent trials required")
    fields = ["baseline", "fault", "post_reset_probe"]
    for doc in documents:
        for key in fields:
            case = doc.get(key)
            if not isinstance(case, dict) or not isinstance(case.get("error_ratio"), (int, float)):
                raise ValueError("invalid experiment schema")
        if doc["baseline"]["failed"] != 0 or doc["post_reset_probe"]["failed"] != 0:
            raise ValueError("invalid baseline or post-reset trial")
        if doc["fault"]["failed"] <= 0:
            raise ValueError("fault did not reproduce in one or more trials")
    return {
        "scope": "synthetic bounded backend capacity in disposable Kind; NOT production MTTR",
        "trials": len(documents),
        "baseline_error_ratio_median": round(statistics.median(
            x["baseline"]["error_ratio"] for x in documents), 4),
        "fault_error_ratio_median": round(statistics.median(
            x["fault"]["error_ratio"] for x in documents), 4),
        "after_manual_reset_error_ratio_median": round(statistics.median(
            x["post_reset_probe"]["error_ratio"] for x in documents), 4),
        "fault_error_ratio_min": min(x["fault"]["error_ratio"] for x in documents),
        "fault_error_ratio_max": max(x["fault"]["error_ratio"] for x in documents),
        "backend_rejections_sum": sum(x["new_backend_rejections"] for x in documents),
        "manual_reset_probe_seconds_median": round(statistics.median(
            x["manual_reset_probe_seconds"] for x in documents), 4),
        "caution": "small sample; synthetic experiment; not a production availability estimate",
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", help="Kind experiment report paths")
    parser.add_argument("--output", default="kind-summary.json")
    args = parser.parse_args()
    docs = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.reports]
    summary = aggregate(docs)
    print(json.dumps(summary, indent=2))
    Path(args.output).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
