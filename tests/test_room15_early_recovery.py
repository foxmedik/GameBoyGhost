import unittest

from gameboy_agent.room15_early_recovery import EarlyY80Recovery


class EarlyY80RecoveryTests(unittest.TestCase):
    def test_intervenes_before_a_terminal_loop(self):
        controller = EarlyY80Recovery(stall_limit=2, left_steps=3)
        self.assertEqual(controller.action({'x': 88, 'y': 80}), (None, False))
        self.assertEqual(controller.action({'x': 88, 'y': 80}), (None, False))
        self.assertEqual(controller.action({'x': 88, 'y': 80}), (['left', 'b'], True))
        self.assertEqual(controller.action({'x': 88, 'y': 80}), (['left', 'b'], True))

    def test_ignores_stationary_combat_away_from_y80(self):
        controller = EarlyY80Recovery(stall_limit=1)
        controller.action({'x': 92, 'y': 78})
        self.assertEqual(controller.action({'x': 92, 'y': 78}), (None, False))


if __name__ == '__main__': unittest.main()
