import unittest

from gameboy_agent.room15_recovery import BypassRecovery, projectile_threat


class ProjectileThreatTests(unittest.TestCase):
    def test_wall_height_and_bounded_recovery(self):
        recovery = BypassRecovery()
        self.assertEqual(recovery.action({'x': 118, 'y': 80}), ('left', False))
        choices = []
        with self.assertRaisesRegex(RuntimeError, 'bypass blocked.*two recovery attempts'):
            for _ in range(160):
                choices.append(recovery.action({'x': 118, 'y': 80}))
        self.assertIn((None, True), choices)
        self.assertIn(('down', True), choices)
        self.assertEqual(recovery.escapes, 2)

    def test_diagonal_collision_from_development_trace(self):
        self.assertEqual(projectile_threat({'x': 95, 'y': 62}, [
            dict(slot=6, x=79, y=56, vx=20, vy=9),
            dict(slot=7, x=89, y=38, vx=4, vy=20),
        ]), 'left')

    def test_receding_and_missed_shots_do_not_interrupt(self):
        self.assertIsNone(projectile_threat({'x': 95, 'y': 62}, [
            dict(slot=6, x=105, y=62, vx=20, vy=0),
            dict(slot=7, x=30, y=40, vx=0, vy=20),
        ]))

    def test_signed_velocity(self):
        self.assertEqual(projectile_threat({'x': 95, 'y': 62}, [
            dict(slot=6, x=115, y=62, vx=236, vy=0),
        ]), 'right')
