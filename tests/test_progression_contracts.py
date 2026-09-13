import unittest
from unittest.mock import patch
from types import SimpleNamespace
from gameboy_agent.progression_contracts import require_stage,settle_and_require_stage,adjacent_direction,StageBlocked

class ContractTests(unittest.TestCase):
    def test_wrong_room_fails_without_actions(self):
        env=SimpleNamespace(pyboy=object())
        state=dict(room=[0,0,0x81],x=40,y=40,health=20,sword=1,inventory=[4,1],tail_key=0)
        with patch('gameboy_agent.progression_contracts.snapshot',return_value=state),patch('gameboy_agent.progression_contracts.mode',return_value='world'):
            with self.assertRaisesRegex(StageBlocked,'expected room.*Tail Key possession'):
                require_stage(env,'tail-cave')
    def test_room_delta_never_wraps_or_raises_keyerror(self):
        for source,destination in (([0,0,0x81],0x51),([0,0,0x0F],0x10),([1,0,0x51],0x41)):
            with self.assertRaises(StageBlocked):adjacent_direction(source,destination)
        self.assertEqual(adjacent_direction([0,0,0x51],0x41),(1,'up'))

    def test_transition_may_settle_before_contract_check(self):
        env=SimpleNamespace(pyboy=object(),step_input_events=lambda **kwargs:None)
        valid=dict(room=[0,0,0x62],x=40,y=40,health=12,sword=1,
                   inventory=[4,1],toadstool=1)
        with patch('gameboy_agent.progression_contracts.snapshot',side_effect=[valid,valid,valid]), \
             patch('gameboy_agent.progression_contracts.mode',side_effect=['transition','world','world']):
            self.assertEqual(settle_and_require_stage(env,'witch-exchange'),valid)
