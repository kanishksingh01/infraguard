import json
import unittest
from unittest.mock import Mock, patch
from guard.remediation import abort_with_preconditions, RemediationError, LAB_CONTEXT
from guard.kubernetes import parse_rollout

def sample():
    return {
        "kind": "Rollout",
        "metadata": {"name": "checkout", "namespace": "infraguard-lab",
                     "uid": "uid123", "resourceVersion": "9876", "generation": 2},
        "spec": {"replicas": 3, "strategy": {"canary": {}}},
        "status": {"phase": "Progressing", "observedGeneration": 2,
                   "readyReplicas": 2, "currentStepIndex": 1}
    }

def evidence():
    return {"decision": "ABORT_RECOMMENDED", "action_executed": False,
            "rollout": parse_rollout(sample()).as_dict()}

class RemediationTests(unittest.TestCase):
    def test_dry_run_refuses_patch(self):
        with self.assertRaisesRegex(RemediationError, "approval"):
            abort_with_preconditions("checkout", evidence(), approved=False,
                                     run=Mock())

    def test_stale_or_missing_evidence_refuses_patch(self):
        with self.assertRaisesRegex(RemediationError, "evidence"):
            abort_with_preconditions("checkout", {"decision": "HOLD"}, approved=True,
                                     run=Mock())

    def test_lab_only_json_patch_checks_uid_and_resource_version(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            if "get" in command:
                return Mock(returncode=0, stdout=json.dumps(sample()))
            return Mock(returncode=0, stdout="{}")
        result = abort_with_preconditions("checkout", evidence(), approved=True, run=runner)
        self.assertTrue(result["action_executed"])
        self.assertEqual(len(calls), 2)
        self.assertIn(LAB_CONTEXT, calls[0])
        self.assertIn(LAB_CONTEXT, calls[1])
        self.assertIn("--subresource=status", calls[1])
        patch_data = json.loads(calls[1][calls[1].index("--patch") + 1])
        self.assertEqual(patch_data[0]["path"], "/metadata/uid")
        self.assertEqual(patch_data[1]["path"], "/metadata/resourceVersion")
        self.assertEqual(patch_data[2]["path"], "/status/abort")
        self.assertIs(patch_data[2]["value"], True)

    def test_rollout_replaced_between_observation_and_abort(self):
        changed = sample()
        changed["metadata"]["generation"] = 3
        def runner(*args, **kwargs):
            return Mock(returncode=0, stdout=json.dumps(changed))
        with self.assertRaisesRegex(RemediationError, "changed"):
            abort_with_preconditions("checkout", evidence(), approved=True, run=runner)

    def test_recreated_rollout_same_generation_is_refused(self):
        changed = sample()
        changed["metadata"]["uid"] = "recreated-uid"
        def runner(*args, **kwargs):
            return Mock(returncode=0, stdout=json.dumps(changed))
        with self.assertRaisesRegex(RemediationError, "changed"):
            abort_with_preconditions("checkout", evidence(), approved=True, run=runner)

    def test_patch_conflict_refuses_success(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            if "get" in command:
                return Mock(returncode=0, stdout=json.dumps(sample()))
            return Mock(returncode=1, stderr="conflict")
        with self.assertRaisesRegex(RemediationError, "conflicted"):
            abort_with_preconditions("checkout", evidence(), approved=True, run=runner)
        self.assertEqual(len(calls), 2)

    def test_nonactive_rollout_refuses_abort(self):
        changed = sample()
        changed["status"]["phase"] = "Healthy"
        def runner(*args, **kwargs):
            return Mock(returncode=0, stdout=json.dumps(changed))
        with self.assertRaisesRegex(RemediationError, "not an active"):
            abort_with_preconditions("checkout", evidence(), approved=True, run=runner)

if __name__ == "__main__":
    unittest.main()
