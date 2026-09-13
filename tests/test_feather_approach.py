import unittest
from unittest.mock import Mock, patch

from gameboy_agent.feather_approach import cross_feather_traps
from gameboy_agent.guided_tail_steps import walk, travel


class FeatherApproachContractTests(unittest.TestCase):
    def test_wrong_room_rejected_before_traps_or_inputs(self):
        env = Mock()
        with patch('gameboy_agent.feather_approach.snapshot', return_value={
            'room': [1, 0, 0x14], 'health': 4,
        }), patch('gameboy_agent.feather_approach.entities') as traps:
            with self.assertRaisesRegex(RuntimeError, 'requires living room1D'):
                cross_feather_traps(env, [])
        traps.assert_not_called()
        env.step_buttons.assert_not_called()

    def test_missing_trap_is_blocker_before_input(self):
        env = Mock()
        state = dict(room=[1, 0, 0x1D], health=4, x=72, y=127, dialog_state=0)
        with patch('gameboy_agent.feather_approach.snapshot', return_value=state), \
                patch('gameboy_agent.feather_approach.entities', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'contract interrupted'):
                cross_feather_traps(env, [])
        env.step_buttons.assert_not_called()

    def test_walk_does_not_accept_coordinate_in_wrong_room(self):
        env = Mock()
        with patch('gameboy_agent.guided_tail_steps.snapshot', return_value={
            'room': [1, 0, 0x15], 'health': 4,
        }):
            with self.assertRaisesRegex(RuntimeError, 'requires living room 14'):
                walk(env, 0x14, 'up', lambda s: True)
        env.step_buttons.assert_not_called()

    def test_travel_rejects_unexpected_destination(self):
        env = Mock()
        with patch('gameboy_agent.guided_tail_steps.snapshot', return_value={
            'room': [1, 0, 0x09], 'health': 4, 'dialog_state': 0,
        }):
            with self.assertRaisesRegex(RuntimeError, 'expected 0E -> 08'):
                travel(env, 0x0E, 'up', 0x08)
        env.step_buttons.assert_not_called()

    def test_dead_destination_is_not_success(self):
        env = Mock()
        with patch('gameboy_agent.guided_tail_steps.snapshot', return_value={
            'room': [1, 0, 0x08], 'health': 0, 'dialog_state': 0,
        }):
            with self.assertRaisesRegex(RuntimeError, 'Transition interrupted'):
                travel(env, 0x0E, 'up', 0x08)
        env.step_buttons.assert_not_called()
