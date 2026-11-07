import unittest
from unittest.mock import patch
from guard.kubernetes import (
    parse_rollout, get_rollout, KubernetesError, combine_rollout_and_slo
)

def rollout(phase="Progressing", observed=2, generation=2):
    return {"apiVersion": "argoproj.io/v1alpha1", "kind": "Rollout",
            "metadata": {"name": "checkout", "namespace": "lab", "generation": generation},
            "spec": {"replicas": 3, "strategy": {"canary": {}}},
            "status": {"phase": phase, "observedGeneration": observed,
                       "readyReplicas": 2, "currentStepIndex": 1}}

class KubernetesTests(unittest.TestCase):
    def test_parse(self):
        state = parse_rollout(rollout())
        self.assertEqual(state.current_step_index, 1)
        self.assertFalse(state.reconciling)
        self.assertEqual(state.desired_replicas, 3)

    def test_stale_rollout_is_held(self):
        state = parse_rollout(rollout(observed=1))
        verdict = combine_rollout_and_slo(state, {"decision": "ABORT_RECOMMENDED"})
        self.assertEqual(verdict["decision"], "HOLD")
        self.assertFalse(verdict["action_executed"])

    def test_active_canary_abort_is_only_recommended(self):
        verdict = combine_rollout_and_slo(
            parse_rollout(rollout()), {"decision": "ABORT_RECOMMENDED"})
        self.assertEqual(verdict["decision"], "ABORT_RECOMMENDED")
        self.assertFalse(verdict["action_executed"])

    def test_finished_rollout_not_aborted(self):
        verdict = combine_rollout_and_slo(
            parse_rollout(rollout(phase="Healthy")), {"decision": "ABORT_RECOMMENDED"})
        self.assertEqual(verdict["decision"], "HOLD")

    def test_missing_observation_not_passed(self):
        verdict = combine_rollout_and_slo(None, {"decision": "PASS"})
        self.assertEqual(verdict["decision"], "HOLD")

    def test_invalid_name_never_invokes_kubectl(self):
        with patch("guard.kubernetes.subprocess.run") as runner:
            with self.assertRaises(ValueError):
                get_rollout("lab;rm -rf /", "checkout")
            runner.assert_not_called()

    def test_kubectl_command_read_only(self):
        import json
        from unittest.mock import Mock
        with patch("guard.kubernetes.subprocess.run") as runner:
            runner.return_value = Mock(returncode=0, stdout=json.dumps(rollout()))
            state = get_rollout("lab", "checkout")
            self.assertEqual(state.phase, "Progressing")
            cmd = runner.call_args.args[0]
            self.assertEqual(cmd[2:5], ["get", "rollouts.argoproj.io", "checkout"])
            self.assertNotIn("patch", cmd)

    def test_invalid_response(self):
        with self.assertRaises(KubernetesError):
            parse_rollout({"kind": "Deployment"})

    def test_unavailable_kubectl(self):
        with patch("guard.kubernetes.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(KubernetesError):
                get_rollout("lab", "checkout")

if __name__ == "__main__":
    unittest.main()
