import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from guard.kubernetes import parse_rollout, KubernetesError
from guard.reconciler import Reconciler, validate_loopback_context

def state(phase="Paused", generation=2, observed=2):
    return parse_rollout({
        "kind": "Rollout",
        "metadata": {"name": "checkout", "namespace": "infraguard-lab",
                     "generation": generation, "uid": "uid-1"},
        "spec": {"replicas": 2},
        "status": {"phase": phase, "observedGeneration": observed,
                   "readyReplicas": 2},
    })

class ReconcilerTests(unittest.TestCase):
    def make_controller(self, **extra):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "policy.json"
        path.write_text(json.dumps({"thresholds": [
            {"name": "errors", "query": "errors", "maximum": 0.05,
             "consecutive_breaches": 2}]}))
        params = {"state_reader": lambda *a, **kw: state(),
                  "metric_reader": lambda *a: .20}
        params.update(extra)
        return Reconciler("checkout", "http://127.0.0.1:9090", str(path), **params)

    def test_read_only_consecutive_breaches(self):
        ctl = self.make_controller()
        self.assertEqual(ctl.step()["decision"], "HOLD")
        result = ctl.step()
        self.assertEqual(result["decision"], "ABORT_RECOMMENDED")
        self.assertNotIn("execution", result)

    def test_stale_generation_clears_streak(self):
        states = iter([state(), state(generation=3, observed=2), state()])
        ctl = self.make_controller(state_reader=lambda *a, **kw: next(states))
        self.assertEqual([ctl.step()["decision"] for _ in range(3)],
                         ["HOLD", "HOLD", "HOLD"])

    def test_unavailable_state_holds(self):
        def broken(*a, **kw):
            raise KubernetesError("down")
        ctl = self.make_controller(state_reader=broken)
        self.assertEqual(ctl.step()["decision"], "HOLD")

    def test_execute_once_with_approval(self):
        calls = []
        def abort(*a, **kw):
            calls.append(kw)
            return {"action_executed": True}
        ctl = self.make_controller(execute=True, approved=True, aborter=abort)
        ctl.step()
        self.assertTrue(ctl.step()["execution"]["action_executed"])
        with self.assertRaisesRegex(Exception, "duplicate"):
            ctl.step()
        self.assertEqual(len(calls), 1)

    def test_context_guard_refuses_nonlocal_api(self):
        def runner(url):
            return lambda *a, **kw: Mock(returncode=0, stdout=json.dumps({
                "clusters": [{"cluster": {"server": url}}]}))
        self.assertEqual(validate_loopback_context(runner("https://127.0.0.1:6443")), "127.0.0.1")
        with self.assertRaises(ValueError):
            validate_loopback_context(runner("https://cluster.example.com:6443"))
        with self.assertRaises(ValueError):
            validate_loopback_context(runner("http://127.0.0.1:6443"))
