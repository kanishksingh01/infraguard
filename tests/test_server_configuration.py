import unittest
from lab.server import LabState

class RevisionConfigurationTests(unittest.TestCase):
    def test_baseline_vs_faulty_revision_configuration(self):
        stable = LabState(capacity=8)
        faulty = LabState(capacity=8)
        faulty.configure(8)
        self.assertEqual(stable.snapshot()["fanout"], 1)
        self.assertEqual(faulty.snapshot()["fanout"], 8)

    def test_unsafe_fanout_is_rejected(self):
        with self.assertRaises(ValueError):
            LabState().configure(99)

if __name__ == "__main__":
    unittest.main()
