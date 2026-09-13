import unittest
from unittest.mock import Mock, patch
from gameboy_agent.boss_door_endpoint import open_boss_door
from gameboy_agent.nightmare_key_route import RouteBlocker


class BossDoorEndpointTests(unittest.TestCase):
    def setUp(self):
        self.env = Mock()
        self.env.frames = 0
        self.env.pyboy.memory = {0xDBCF: 1, 0xD90B: 0, 0xC188: 0, 0xDB94: 0}
        self.state = dict(room=[1, 0, 11], health=4, x=80, y=32, dialog_state=0)
        for target in ['gameboy_agent.boss_door_endpoint.snapshot', 'gameboy_agent.nightmare_key_route.snapshot']:
            p = patch(target, side_effect=lambda _: dict(self.state))
            p.start(); self.addCleanup(p.stop)
        p = patch('gameboy_agent.nightmare_key_route.mode', return_value='world')
        p.start(); self.addCleanup(p.stop)

    def test_wrong_room_rejected_before_input(self):
        self.state['room'] = [1, 0, 16]
        with self.assertRaisesRegex(RouteBlocker, 'Expected room 0B'):
            open_boss_door(self.env)
        self.env.step_buttons.assert_not_called()

    def test_missing_key_rejected(self):
        self.env.pyboy.memory[0xDBCF] = 0
        with self.assertRaisesRegex(RouteBlocker, 'requires Nightmare Key'):
            open_boss_door(self.env)
        self.env.step_buttons.assert_not_called()

    def test_already_open_is_not_new_success(self):
        self.env.pyboy.memory[0xD90B] = 4
        with self.assertRaisesRegex(RouteBlocker, 'already open'):
            open_boss_door(self.env)
        self.env.step_buttons.assert_not_called()

    def test_pending_damage_is_not_a_safe_finish(self):
        self.env.pyboy.memory[0xDB94] = 4
        with self.assertRaisesRegex(RouteBlocker, 'settled door and health'):
            open_boss_door(self.env)
        self.env.step_buttons.assert_not_called()

    def test_opening_releases_movement_and_waits_for_animation(self):
        commands = []
        def step(buttons, **kwargs):
            commands.append(buttons)
            self.env.frames += 1
            if len(commands) == 1:
                self.env.pyboy.memory[0xD90B] = 4
                self.env.pyboy.memory[0xC188] = 1
            elif len(commands) == 2:
                self.env.pyboy.memory[0xC188] = 0
        self.env.step_buttons.side_effect = step
        result = open_boss_door(self.env)
        self.assertEqual(commands, [['up'], [], []])
        self.assertEqual(result['status'], 'boss_door_opened_alive_outside')

    def test_crossing_into_boss_room_is_not_success(self):
        def step(*args, **kwargs):
            self.state['room'] = [1, 0, 6]
            self.env.pyboy.memory[0xD90B] = 4
        self.env.step_buttons.side_effect = step
        with self.assertRaisesRegex(RouteBlocker, 'left antechamber'):
            open_boss_door(self.env)

    def test_opening_that_never_settles_is_bounded_failure(self):
        def step(*args, **kwargs):
            self.env.pyboy.memory[0xC188] = 1
            self.env.pyboy.memory[0xD90B] = 4
        self.env.step_buttons.side_effect = step
        with self.assertRaisesRegex(RouteBlocker, 'budget exhausted'):
            open_boss_door(self.env, budget=5)
        self.assertEqual(self.env.step_buttons.call_count, 5)


if __name__ == '__main__':
    unittest.main()
