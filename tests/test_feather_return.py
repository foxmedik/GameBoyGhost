import unittest
from types import SimpleNamespace
from unittest.mock import patch
from gameboy_agent.feather_return import settle


class FeatherSettlementTests(unittest.TestCase):
    def test_healing_started_on_final_neutral_is_not_settled(self):
        memory=bytearray(65536)
        env=SimpleNamespace(pyboy=SimpleNamespace(memory=memory),frames=0)
        def step(buttons,**kwargs):
            self.assertEqual(buttons,[])
            env.frames+=1
            memory[0xDB93]=1 if env.frames==1 else 0
        env.step_buttons=step
        with patch('gameboy_agent.feather_return.SafeRouteSteps'):
            settle(env,28,budget=4)
        self.assertEqual(env.frames,3)
