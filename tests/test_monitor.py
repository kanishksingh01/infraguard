import json
import tempfile
import unittest
from unittest.mock import patch
from guard.monitor import monitor
from guard.kubernetes import parse_rollout

def active():
    return parse_rollout({
        "kind": "Rollout", "metadata": {"name": "checkout", "namespace": "lab",
            "generation": 2, "uid": "u1"},
        "spec": {"replicas": 2},
        "status": {"phase": "Progressing", "observedGeneration": 2}})

class MonitorTests(unittest.TestCase):
    def test_sustained_breach_across_three_cycles(self):
        with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8") as policy:
            json.dump({"thresholds": [{"name": "errors", "query": "up",
                       "maximum": 0.05, "consecutive_breaches": 2}]}, policy)
            policy.flush()
            with patch("guard.monitor.get_rollout", return_value=active()), \
                 patch("guard.monitor.fetch_scalar", side_effect=[0.01, 0.2, 0.3]):
                decisions = list(monitor("lab", "checkout", "http://127.0.0.1:9090",
                                         policy.name, iterations=3, interval=0,
                                         context="kind-infraguard", sleeper=lambda _: None))
        self.assertEqual([d["decision"] for d in decisions],
                         ["PASS", "HOLD", "ABORT_RECOMMENDED"])
        self.assertTrue(all(not d["action_executed"] for d in decisions))
        self.assertTrue(all(d["execution_mode"] == "observe_only" for d in decisions))

    def test_missing_rollout_does_not_pass(self):
        with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8") as policy:
            json.dump({"thresholds": [{"name": "errors", "query": "up",
                       "maximum": .05}]}, policy)
            policy.flush()
            with patch("guard.monitor.get_rollout", side_effect=Exception("unexpected")):
                # Unexpected exceptions should not silently be converted into PASS.
                with self.assertRaises(Exception):
                    list(monitor("lab", "checkout", "http://127.0.0.1:9090",
                                 policy.name, iterations=1, interval=0,
                                 context="kind-infraguard"))

    def test_context_required(self):
        with self.assertRaises(ValueError):
            list(monitor("lab", "checkout", "http://127.0.0.1:9090",
                         "missing.json", context=None))

if __name__ == "__main__":
    unittest.main()
