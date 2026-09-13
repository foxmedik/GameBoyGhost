import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from gameboy_agent.rolling_bones_spacing import fight
from gameboy_agent.nightmare_key_return import reach_rolling_bones
from gameboy_agent.nightmare_key_route import RouteBlocker


class CombatSettlementTests(unittest.TestCase):
    def test_shutter_starting_on_final_step_prevents_premature_success(self):
        memory = bytearray(65536)
        memory[0xDB00:0xDB02] = bytes([10, 1])
        memory[0xDBCF] = 1
        memory[0xD911] = 32
        env = SimpleNamespace(pyboy=SimpleNamespace(memory=memory), frames=0)

        def step(buttons, **kwargs):
            self.assertEqual(buttons, [])
            env.frames += 1
            memory[0xC188] = 1 if env.frames == 1 else 0

        env.step_buttons = step
        with patch('gameboy_agent.rolling_bones_spacing.SafeRouteSteps') as route:
            route.return_value.check.return_value = {'dialog_state': 0}
            result = fight(env, [], budget=3)
        self.assertTrue(result['success'])
        self.assertEqual(env.frames, 2)

    def test_wrong_return_room_rejected_before_inventory_and_movement(self):
        env = Mock()
        with patch('gameboy_agent.nightmare_key_route.snapshot',
                   return_value=dict(room=[1, 0, 6], health=24)):
            with self.assertRaisesRegex(RouteBlocker, 'Expected room 08'):
                reach_rolling_bones(env)
        env.step_buttons.assert_not_called()
