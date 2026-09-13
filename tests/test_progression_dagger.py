import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("progression_dagger", ROOT / "scripts/collect_progression_dagger_v1.py")
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)


class ProgressionDaggerTests(unittest.TestCase):
    def test_duration_and_history_encoding(self):
        commands = [{"buttons": ["down", "b"], "action_frames": 3},
                    {"buttons": ["a"], "action_frames": 10}]
        self.assertEqual(MODULE.action_tuple(commands[0]), (2, 2, 1))
        self.assertEqual(MODULE.action_tuple(commands[1]), (0, 1, 2))
        history = MODULE.history_features(commands)
        self.assertEqual(history.shape, (12,))
        self.assertEqual(history[-6:].tolist(), [0.5, 1.0, 0.5, 0.0, 0.5, 1.0])


if __name__ == "__main__": unittest.main()
