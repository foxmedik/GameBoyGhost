import unittest
from unittest.mock import Mock, patch
from gameboy_agent.boss_door_route import SafeRouteSteps, cross_room10
from gameboy_agent.nightmare_key_route import RouteBlocker


class OnwardSafetyTests(unittest.TestCase):
    def test_positive_health_during_fall_is_not_safe(self):
        env = Mock(); env.pyboy.memory = {0xDB94: 0, 0xC11C: 6}
        with patch('gameboy_agent.nightmare_key_route.snapshot', return_value=dict(room=[1,0,16], health=4)), \
                patch('gameboy_agent.nightmare_key_route.mode', return_value='world'):
            with self.assertRaisesRegex(RouteBlocker, 'falling into a pit'):
                SafeRouteSteps(env).check(16)
        env.step_buttons.assert_not_called()

    def test_buffered_damage_rejected_before_movement(self):
        env = Mock(); env.pyboy.memory = {0xDB94: 4, 0xC11C: 0}
        with patch('gameboy_agent.nightmare_key_route.snapshot', return_value=dict(room=[1,0,16], health=4)), \
                patch('gameboy_agent.nightmare_key_route.mode', return_value='world'):
            with self.assertRaisesRegex(RouteBlocker, 'Damage is still being applied'):
                SafeRouteSteps(env).move(16, 'right', lambda s: True)
        env.step_buttons.assert_not_called()

    def test_wrong_room_precedes_spark_lookup(self):
        env = Mock()
        with patch('gameboy_agent.nightmare_key_route.snapshot', return_value=dict(room=[1,0,17], health=4)):
            with self.assertRaisesRegex(RouteBlocker, 'Expected room 10'):
                cross_room10(env)
        env.step_buttons.assert_not_called()

    def test_reactive_passage_attacks_new_threat_and_stops_on_pending_damage(self):
        from gameboy_agent.boss_door_route import armed_move
        env=Mock();m=bytearray(65536);env.pyboy.memory=m
        m[0xDB01]=1;m[0xC280]=5;m[0xC3A0]=30
        m[0xC200],m[0xC210]=150,110
        state=dict(room=[1,0,15],health=24,x=100,y=110)
        calls=[]
        def step(buttons,**kwargs):
            calls.append(list(buttons));state['x']+=1
            if len(calls)==1:m[0xC200]=120
            else:m[0xDB94]=4
        env.step_buttons.side_effect=step
        with patch('gameboy_agent.nightmare_key_route.snapshot',side_effect=lambda _:dict(state)), \
             patch('gameboy_agent.nightmare_key_route.mode',return_value='world'):
            with self.assertRaisesRegex(RouteBlocker,'Damage is still being applied'):
                armed_move(env,15,'right',lambda s:False,reactive_stalfos=True)
        self.assertEqual(calls,[['right'],['right','a']])
        self.assertEqual(state['health'],24)

    def test_reactive_keese_defense_settles_turns_and_rejects_buffered_damage(self):
        from gameboy_agent.boss_door_route import armed_move
        env=Mock();m=bytearray(65536);env.pyboy.memory=m
        m[0xDB01]=1;m[0xC280]=5;m[0xC3A0]=25
        m[0xC200],m[0xC210]=37,50
        m[0xFF9E]=1;m[0xC137]=2
        state=dict(room=[1,0,15],health=24,x=43,y=32)
        calls=[]
        def step(buttons,**kwargs):
            calls.append(list(buttons))
            if not buttons:m[0xC137]=0
            elif buttons==['down']:m[0xFF9E]=3
            elif buttons==['a']:m[0xDB94]=4
        env.step_buttons.side_effect=step
        with patch('gameboy_agent.nightmare_key_route.snapshot',return_value=state), \
             patch('gameboy_agent.nightmare_key_route.mode',return_value='world'):
            with self.assertRaisesRegex(RouteBlocker,'Damage is still being applied'):
                armed_move(env,15,'left',lambda s:False,reactive_enemies=True)
        self.assertEqual(calls,[[],['down'],['a']])
        self.assertEqual(state['health'],24)
