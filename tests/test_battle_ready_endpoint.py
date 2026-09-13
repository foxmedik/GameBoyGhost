import unittest
from unittest.mock import Mock, patch
from gameboy_agent.battle_ready_endpoint import require_battle_ready, open_battle_ready_door
from gameboy_agent.nightmare_key_route import RouteBlocker


class BattleReadyTests(unittest.TestCase):
    def setUp(self):
        self.env = Mock()
        self.env.pyboy.memory = {0xDB93:0, 0xDB94:0, 0xC11C:0, 0xFFA2:0}
        self.state = dict(room=[1,0,11], health=24, max_hearts=3, inventory=[10,1], dialog_state=0)
        p=patch('gameboy_agent.battle_ready_endpoint.snapshot', side_effect=lambda _:dict(self.state))
        p.start();self.addCleanup(p.stop)
        p=patch('gameboy_agent.battle_ready_endpoint.mode',return_value='world')
        p.start();self.addCleanup(p.stop)

    def test_half_heart_rejected_before_door_input(self):
        self.state['health']=4
        with patch('gameboy_agent.battle_ready_endpoint.open_boss_door') as door:
            with self.assertRaisesRegex(RouteBlocker,'4/24'):
                open_battle_ready_door(self.env)
        door.assert_not_called()

    def test_full_means_actual_capacity(self):
        self.state.update(max_hearts=4,health=24)
        with self.assertRaisesRegex(RouteBlocker,'24/32'):
            require_battle_ready(self.env)
        self.state['health']=32
        self.assertEqual(require_battle_ready(self.env)['health'],32)

    def test_pending_heal_is_not_full_readiness(self):
        self.env.pyboy.memory[0xDB93]=1
        with self.assertRaisesRegex(RouteBlocker,'still changing'):
            require_battle_ready(self.env)

    def test_wrong_loadout_is_blocker(self):
        self.state['inventory']=[4,1]
        with self.assertRaisesRegex(RouteBlocker,'loadout'):
            require_battle_ready(self.env)

    def test_wrong_room_precedes_other_state_reads(self):
        self.state={'room':[1,0,6]}
        with self.assertRaisesRegex(RouteBlocker,'antechamber'):
            require_battle_ready(self.env)

    def test_health_must_remain_full_after_opening(self):
        def opened(*args,**kwargs):
            self.state['health']=20
            return {'status':'boss_door_opened_alive_outside'}
        with patch('gameboy_agent.battle_ready_endpoint.open_boss_door',side_effect=opened):
            with self.assertRaisesRegex(RouteBlocker,'20/24'):
                open_battle_ready_door(self.env)

    def test_success_reports_version_and_capacity(self):
        with patch('gameboy_agent.battle_ready_endpoint.open_boss_door',return_value={'opened_frame':123}):
            result=open_battle_ready_door(self.env)
        self.assertEqual(result['status'],'boss_door_opened_full_health_ready')
        self.assertEqual(result['health_capacity'],24)
