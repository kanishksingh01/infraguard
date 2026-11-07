import unittest
from lab.aggregate import aggregate

def trial(fault_ratio=0.8):
    return {
        "baseline": {"failed": 0, "error_ratio": 0.0},
        "fault": {"failed": 8, "error_ratio": fault_ratio},
        "post_reset_probe": {"failed": 0, "error_ratio": 0.0},
        "new_backend_rejections": 42,
        "manual_reset_probe_seconds": 0.07,
    }

class AggregateTests(unittest.TestCase):
    def test_summary_of_multiple_trials(self):
        report = aggregate([trial(.8), trial(.9), trial(1)])
        self.assertEqual(report["trials"], 3)
        self.assertEqual(report["fault_error_ratio_median"], .9)
        self.assertEqual(report["backend_rejections_sum"], 126)
        self.assertEqual(report["baseline_error_ratio_median"], 0)

    def test_unsafe_or_bad_trials_rejected(self):
        with self.assertRaises(ValueError):
            aggregate([trial()])
        bad = trial()
        bad["post_reset_probe"]["failed"] = 1
        with self.assertRaises(ValueError):
            aggregate([trial(), bad])
        bad = trial()
        bad["fault"]["failed"] = 0
        with self.assertRaises(ValueError):
            aggregate([trial(), bad])

if __name__ == "__main__":
    unittest.main()
