import unittest
from unittest.mock import Mock, patch

from gameboy_agent.nightmare_key_route import RouteBlocker, RouteSteps, upper_staircase_approach


class NightmareRouteContracts(unittest.TestCase):
    def state(self, room=8, **kwargs):
        return dict(room=[1, 0, room], health=4, x=75, y=127, **kwargs)

    def test_wrong_room_before_inventory_or_route(self):
        env = Mock()
        with patch('gameboy_agent.nightmare_key_route.snapshot', return_value=self.state(15)):
            with self.assertRaisesRegex(RouteBlocker, 'Expected room 08'):
                upper_staircase_approach(env)
        env.step_buttons.assert_not_called()

    def test_lower_entry_cannot_satisfy_upper_entry_contract(self):
        env = Mock()
        state = dict(room=[1, 0, 15], health=4, x=11, y=86)
        with patch('gameboy_agent.nightmare_key_route.snapshot', return_value=state), \
                patch('gameboy_agent.nightmare_key_route.mode', return_value='world'):
            with self.assertRaisesRegex(RouteBlocker, 'upper west'):
                RouteSteps(env).require(15, lambda s: s['y'] <= 50, 'upper west entry required')
        env.step_buttons.assert_not_called()

    def test_health_loss_rejected_even_at_target_position(self):
        env = Mock()
        with patch('gameboy_agent.nightmare_key_route.snapshot', side_effect=[self.state(), self.state(8) | {'health': 3}]):
            route = RouteSteps(env)
            with self.assertRaisesRegex(RouteBlocker, 'Health interrupted'):
                route.move(8, 'down', lambda s: True)
        env.step_buttons.assert_not_called()

    def test_jump_rejects_wrong_equipment(self):
        env = Mock()
        env.pyboy.memory = {0xDB00: 4}
        with patch('gameboy_agent.nightmare_key_route.snapshot', return_value=self.state()), \
                patch('gameboy_agent.nightmare_key_route.mode', return_value='world'):
            with self.assertRaisesRegex(RouteBlocker, 'feather equipped'):
                RouteSteps(env).move(8, 'left', lambda s: False, jump=True)
        env.step_buttons.assert_not_called()

    def test_wrong_destination_fails_immediately(self):
        env = Mock()
        with patch('gameboy_agent.nightmare_key_route.snapshot', side_effect=[self.state(), self.state(), self.state(14), self.state(14)]), \
                patch('gameboy_agent.nightmare_key_route.mode', return_value='world'):
            with self.assertRaisesRegex(RouteBlocker, 'Expected room 08'):
                RouteSteps(env).travel(8, 'down', 9)
        self.assertEqual(env.step_buttons.call_count, 1)


if __name__ == '__main__':
    unittest.main()
