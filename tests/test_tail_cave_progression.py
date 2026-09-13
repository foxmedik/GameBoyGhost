import unittest
from unittest.mock import Mock, patch

from gameboy_agent.tail_cave_progression import GelTeacher, enter_compass_room


class GelTeacherTests(unittest.TestCase):
    def test_wrong_room_blocks_before_movement(self):
        env = Mock()
        with patch('gameboy_agent.tail_cave_progression.snapshot', return_value={
            'room': [1, 0, 0x17], 'health': 4,
        }), patch('gameboy_agent.tail_cave_progression.move_until') as move:
            env.pyboy.memory = {0xDBD0: 1}
            with self.assertRaisesRegex(RuntimeError, 'requires living Tail Cave room 16'):
                enter_compass_room(env, [])
            move.assert_not_called()
            env.step_input_events.assert_not_called()

    def test_approach_holds_shield(self):
        teacher = GelTeacher()
        self.assertEqual(
            teacher.action({"x": 120, "y": 68}, [{"x": 72, "y": 68}]),
            (["left", "b"], 1),
        )

    def test_close_attack_faces_and_swings_in_one_command(self):
        teacher = GelTeacher()
        state = {"x": 52, "y": 68}
        targets = [{"x": 72, "y": 68}]
        self.assertEqual(teacher.action(state, targets), (["right", "a"], 10))
        self.assertEqual(teacher.action(state, targets), ([], 3))


if __name__ == "__main__":
    unittest.main()
