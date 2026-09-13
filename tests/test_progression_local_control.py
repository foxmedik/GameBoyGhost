import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("progression_local_control", ROOT / "scripts/progression_local_control.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProgressionLocalControlTests(unittest.TestCase):
    def state(self, room, *, toadstool=0, powder=0, tarin=0):
        return {"room": [0, 0, room], "toadstool": toadstool, "powder": powder, "tarin": tarin}

    def test_focus_room_goals_follow_quest_state(self):
        self.assertEqual(MODULE.destination(self.state(0x52)), 0x62)
        self.assertEqual(MODULE.destination(self.state(0x52, toadstool=1)), 0x42)
        self.assertEqual(MODULE.destination(self.state(0x42, toadstool=1)), 0x43)
        self.assertEqual(MODULE.destination(self.state(0x42, powder=24)), 0x52)
        self.assertIsNone(MODULE.destination(self.state(0x42, powder=24, tarin=1)))

    def test_physical_command_labels(self):
        self.assertEqual(MODULE.command_label({"buttons": ["left", "a"], "action_frames": 10}), [3, 1])
        self.assertEqual(MODULE.command_label({"buttons": ["b"], "action_frames": 3}), [0, 2])
        self.assertIsNone(MODULE.command_label({"buttons": ["start"], "action_frames": 1}))
        self.assertIsNone(MODULE.command_label({"buttons": ["up"], "action_frames": 1,
                                                "timing": "emulated_frames"}))


if __name__ == "__main__":
    unittest.main()
