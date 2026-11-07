import unittest
from lab.experiment import experiment

class ExperimentTests(unittest.TestCase):
    def test_baseline_and_fault_multiplier(self):
        report = experiment(requests=4, concurrency=1, capacity=8)
        self.assertEqual(report["baseline"]["successful"], 4)
        self.assertEqual(report["attempts_per_gateway_request"]["baseline"], 1)
        self.assertEqual(report["attempts_per_gateway_request"]["faulty_rollout"], 8)

if __name__ == "__main__":
    unittest.main()
