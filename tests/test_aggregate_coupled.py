import unittest
from lab.aggregate_coupled import aggregate

def trial(seconds=12, faults=72, concurrency=4):
    return {
        "fault_load_concurrency": concurrency,
        "baseline_service": {"requests": 24, "failed": 0},
        "service_after_abort": {"requests": 24, "failed": 0},
        "slo_decision": "ABORT_RECOMMENDED",
        "guarded_abort": {"action_executed": True},
        "faulty_canary_failed_requests": faults,
        "faulty_canary_successful_requests": 8,
        "abort_to_stable_service_verification_seconds": seconds,
    }

class CoupledAggregateTests(unittest.TestCase):
    def test_median_and_bounds(self):
        a = aggregate([trial(9, concurrency=4), trial(12, concurrency=6), trial(18, concurrency=8)])
        self.assertEqual(a["trials"], 3)
        self.assertEqual(a["abort_to_stable_verification_seconds"]["median"], 12)
        self.assertEqual(a["abort_to_stable_verification_seconds"]["min"], 9)
        self.assertTrue(a["verified_abort_and_service_recovery_in_every_trial"])

    def test_reject_missing_service_recovery(self):
        bad = trial()
        bad["service_after_abort"]["failed"] = 2
        with self.assertRaisesRegex(ValueError, "complete availability"):
            aggregate([trial(concurrency=4), bad, trial(concurrency=8)])

    def test_reject_absent_abort_and_missing_trials(self):
        with self.assertRaisesRegex(ValueError, "three independent"):
            aggregate([trial(), trial()])
        bad = trial()
        bad["guarded_abort"]["action_executed"] = False
        with self.assertRaisesRegex(ValueError, "verified abort"):
            aggregate([trial(concurrency=4), trial(concurrency=6), bad])

    def test_reject_duplicate_load_levels(self):
        with self.assertRaisesRegex(ValueError, "independent load levels"):
            aggregate([trial(), trial(), trial()])

    def test_reject_invalid_duration(self):
        with self.assertRaisesRegex(ValueError, "numeric"):
            aggregate([trial(concurrency=4), trial(float("nan"), concurrency=6), trial(concurrency=8)])

if __name__ == "__main__":
    unittest.main()
