import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from gameboy_agent.room15_takeover import BoundedInputs, EncounterTakeover, TakeoverBlocked
from run_room15_takeover_gate import verify_row


class FakeInputs:
    def __init__(self):
        self.frames = 0
        self.pyboy = None
    def step_buttons(self, buttons, action_frames=1):
        self.frames += action_frames
    def step_input_events(self, buttons=(), frames=1, **kwargs):
        self.frames += frames


class TakeoverTests(unittest.TestCase):
    def test_nested_dialogue_wait_is_bounded_before_execution(self):
        env = FakeInputs()
        controller = BoundedInputs(env, max_commands=2, max_frames=121)
        controller.step_buttons(['b'])
        controller.step_input_events(frames=120)
        self.assertEqual(env.frames, 121)
        with self.assertRaises(TakeoverBlocked):
            controller.step_input_events(frames=1)
        self.assertEqual(env.frames, 121)

    def test_oversize_wait_never_executes(self):
        env = FakeInputs()
        with self.assertRaises(TakeoverBlocked):
            BoundedInputs(env, max_frames=119).step_input_events(frames=120)
        self.assertEqual(env.frames, 0)

    @patch('gameboy_agent.room15_takeover.snapshot', return_value={'room':[1,0,22],'health':4})
    def test_wrong_room_does_not_invoke_teacher(self, _):
        with patch('gameboy_agent.room15_takeover.clear_compass_room') as teacher:
            with self.assertRaises(TakeoverBlocked):
                EncounterTakeover().run(FakeInputs(), [])
            teacher.assert_not_called()

    def test_second_takeover_is_rejected(self):
        controller = EncounterTakeover()
        controller.used = True
        with patch('gameboy_agent.room15_takeover.snapshot', return_value={'room':[1,0,21],'health':4}):
            with self.assertRaises(TakeoverBlocked):
                controller.run(FakeInputs(), [])

    def test_corrupt_replay_is_rejected(self):
        with patch('run_room15_takeover_gate.fingerprint', return_value='actual'):
            with self.assertRaisesRegex(RuntimeError, 'exact replay mismatch'):
                verify_row(FakeInputs(), {'fingerprint':'corrupt','decision':0}, {})


if __name__ == '__main__':
    unittest.main()
