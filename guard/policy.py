"""Explicit, deterministic canary SLO policy. No mutations."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Threshold:
    name: str
    query: str
    maximum: float
    consecutive_breaches: int = 2

    def __post_init__(self):
        if not self.name or not self.query:
            raise ValueError("name and query required")
        if not math.isfinite(self.maximum):
            raise ValueError("maximum must be finite")
        if self.consecutive_breaches < 1:
            raise ValueError("consecutive_breaches must be positive")

@dataclass(frozen=True)
class Finding:
    metric: str
    value: float | None
    threshold: float
    verdict: str
    consecutive_breaches: int
    evidence: str

class Evaluator:
    """No data / malformed data -> HOLD, not automatic abort."""
    def __init__(self, thresholds: list[Threshold]):
        if not thresholds:
            raise ValueError("at least one threshold required")
        if len({t.name for t in thresholds}) != len(thresholds):
            raise ValueError("metric names must be unique")
        self.thresholds = thresholds
        self.streaks = {t.name: 0 for t in thresholds}

    def evaluate(self, samples: dict[str, float | None]) -> dict:
        findings = []
        for threshold in self.thresholds:
            value = samples.get(threshold.name)
            if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
                self.streaks[threshold.name] = 0
                finding = Finding(threshold.name, None, threshold.maximum, "HOLD", 0,
                                  "missing, non-scalar or non-finite metrics; do not promote")
            elif value > threshold.maximum:
                self.streaks[threshold.name] += 1
                streak = self.streaks[threshold.name]
                verdict = "ABORT_RECOMMENDED" if streak >= threshold.consecutive_breaches else "HOLD"
                finding = Finding(threshold.name, float(value), threshold.maximum,
                                  verdict, streak, "above maximum threshold")
            else:
                self.streaks[threshold.name] = 0
                finding = Finding(threshold.name, float(value), threshold.maximum,
                                  "PASS", 0, "within maximum threshold")
            findings.append(finding)
        from dataclasses import asdict
        overall = ("ABORT_RECOMMENDED" if any(f.verdict == "ABORT_RECOMMENDED" for f in findings)
                   else "HOLD" if any(f.verdict == "HOLD" for f in findings) else "PASS")
        return {"decision": overall, "findings": [asdict(f) for f in findings],
                "dry_run": True, "action_executed": False}
