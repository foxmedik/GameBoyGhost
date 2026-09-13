import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from gameboy_agent.half_heart_setup import prepare_half_heart
from gameboy_agent.nightmare_key_route import RouteBlocker

class PhysicalHalfHeartTests(unittest.TestCase):
    def environment(self,hp,pending=0):
        memory=bytearray(65536)
        memory[0xDB00:0xDB02]=bytes([4,1]);memory[0xDBD0]=1
        memory[0xDB94]=pending
        return SimpleNamespace(pyboy=SimpleNamespace(memory=memory),frames=0,step_buttons=Mock()),dict(room=[1,0,24],health=hp,dialog_state=0,x=136,y=110)

    def test_pending_damage_cannot_undershoot_target(self):
        env,state=self.environment(6,4)
        with patch('gameboy_agent.half_heart_setup.snapshot',return_value=state):
            with self.assertRaisesRegex(RouteBlocker,'undershoot'):
                prepare_half_heart(env,[])
        env.step_buttons.assert_not_called()

    def test_enemy_clear_at_higher_health_is_not_challenge(self):
        env,state=self.environment(12)
        with patch('gameboy_agent.half_heart_setup.snapshot',return_value=state):
            with self.assertRaisesRegex(RouteBlocker,'before actual half-heart'):
                prepare_half_heart(env,[])
        env.step_buttons.assert_not_called()

    def test_settled_four_health_is_required_for_completion(self):
        env,state=self.environment(4)
        before=bytes(env.pyboy.memory);evidence=[]
        with patch('gameboy_agent.half_heart_setup.snapshot',return_value=state):
            prepare_half_heart(env,evidence)
        self.assertEqual(bytes(env.pyboy.memory),before)
        self.assertEqual(evidence[-1]['kind'],'physical_half_heart_setup_complete')
        env.step_buttons.assert_not_called()
