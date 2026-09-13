import unittest

from gameboy_agent.room15_model import ACTIONS
from gameboy_agent.room15_model_v3 import intent, temporal_feature, update


class Room15TemporalFeatureTests(unittest.TestCase):
    def test_failed_down_intent_is_distinct_from_stationary_combat(self):
        down = ACTIONS.index((('down', 'b'), 1))
        shield = ACTIONS.index((('b',), 1))
        blocked = update([], down, {'x': 90, 'y': 80}, {'x': 90, 'y': 80})
        combat = update([], shield, {'x': 90, 'y': 80}, {'x': 90, 'y': 80})
        self.assertEqual(intent(down), (0, 1))
        self.assertNotEqual(blocked, combat)
        observation = {'state': {'x': 90, 'y': 80, 'health': 4}, 'entities': []}
        self.assertNotEqual(temporal_feature(observation, blocked).tolist(), temporal_feature(observation, combat).tolist())

    def test_successful_intent_records_observed_displacement(self):
        left = ACTIONS.index((('left', 'b'), 1))
        self.assertEqual(update([], left, {'x': 90, 'y': 80}, {'x': 87, 'y': 80}), [(left, -3, 0)])
