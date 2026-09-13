import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from gameboy_agent.dungeon_items import ItemSteps
from gameboy_agent.nightmare_key_route import RouteBlocker


class ItemInterruptionTests(unittest.TestCase):
    def environment(self):
        memory = bytearray(65536)
        env = SimpleNamespace(pyboy=SimpleNamespace(memory=memory), frames=0)
        env.step_buttons = Mock()
        return env

    def state(self, **changes):
        return dict(room=[1, 0, 21], health=24, x=57, y=88,
                    dialog_state=0, dialog_id=0, **changes)

    def test_buffered_damage_rejected_before_movement(self):
        env = self.environment()
        env.pyboy.memory[0xDB94] = 4
        with patch('gameboy_agent.dungeon_items.snapshot', return_value=self.state()):
            route = ItemSteps(env)
            with self.assertRaisesRegex(RouteBlocker, 'buffered damage'):
                route.move(21, 'left', lambda s: False)
        env.step_buttons.assert_not_called()

    def test_pending_power_receipt_is_settled_before_done(self):
        env = self.environment()
        env.pyboy.memory[0xC1A9] = 1
        state = self.state()
        def step(buttons, **kwargs):
            self.assertEqual(buttons, [])
            state.update(dialog_state=1, dialog_id=8)
        def dismiss(_):
            state.update(dialog_state=0)
            env.pyboy.memory[0xC1A9] = 0
            env.step_buttons.side_effect = None
        env.step_buttons.side_effect = step
        with patch('gameboy_agent.dungeon_items.snapshot', side_effect=lambda _: dict(state)), \
             patch('gameboy_agent.dungeon_items.mode', return_value='world'), \
             patch('gameboy_agent.dungeon_items.dismiss_dialogue', side_effect=dismiss) as receipt:
            route = ItemSteps(env)
            route.move(21, 'left', lambda s: True)
        receipt.assert_called_once_with(env)
        self.assertEqual(env.step_buttons.call_count, 2)

    def test_chest_dialogue_without_inventory_grant_is_failure(self):
        env = self.environment()
        state = self.state()
        def step(*args, **kwargs):
            state.update(dialog_state=1, dialog_id=0xA7)
        env.step_buttons.side_effect = step
        with patch('gameboy_agent.dungeon_items.snapshot', side_effect=lambda _: dict(state)), \
             patch('gameboy_agent.dungeon_items.mode', return_value='world'), \
             patch('gameboy_agent.dungeon_items.dismiss_dialogue') as receipt:
            route = ItemSteps(env)
            with self.assertRaisesRegex(RouteBlocker, 'expected item/count'):
                route.chest(21, 0xDBCD, 1, 0xA7)
        receipt.assert_not_called()

    def test_goomba_swing_waits_for_observed_facing(self):
        from gameboy_agent.dungeon_items import clear_goombas
        env = self.environment()
        m = env.pyboy.memory
        m[0xFF9E] = 1
        m[0xC280] = 5
        m[0xC3A0] = 159
        m[0xC200], m[0xC210] = 72, 88
        calls = []
        def step(buttons, **kwargs):
            calls.append(list(buttons))
            env.frames += 1
            if 'right' in buttons:
                self.assertNotIn('a', buttons)
                m[0xFF9E] = 0
            if 'a' in buttons:
                self.assertEqual(m[0xFF9E], 0)
                m[0xC280] = 0
        env.step_buttons.side_effect = step
        with patch('gameboy_agent.dungeon_items.snapshot', return_value=self.state()), \
             patch('gameboy_agent.dungeon_items.mode', return_value='world'):
            clear_goombas(env, 21, budget=3)
        self.assertEqual(calls, [['b', 'right'], ['b', 'a'], []])

    def test_travel_settles_acorn_before_continuing_exit(self):
        env=self.environment()
        state=self.state()
        calls=[]
        def step(buttons,**kwargs):
            calls.append(buttons)
            if len(calls)==1:
                state.update(dialog_state=130,dialog_id=0xEC)
            else:
                self.assertEqual(state['dialog_state'],0)
                state['room']=[1,0,22]
        def dismiss(_):state.update(dialog_state=0)
        env.step_buttons.side_effect=step
        with patch('gameboy_agent.dungeon_items.snapshot',side_effect=lambda _:dict(state)), \
             patch('gameboy_agent.dungeon_items.mode',return_value='world'), \
             patch('gameboy_agent.dungeon_items.dismiss_dialogue',side_effect=dismiss) as receipt:
            result=ItemSteps(env).travel(21,'right',22,budget=3)
        receipt.assert_called_once_with(env)
        self.assertEqual(result['room'],[1,0,22])

    def test_stalfos_approach_does_not_hold_retreat_trigger(self):
        from gameboy_agent.dungeon_items import clear_map_enemies
        env=self.environment()
        m=env.pyboy.memory
        m[0xC280],m[0xC3A0]=5,30
        m[0xC200],m[0xC210]=90,88
        m[0xFF9E]=1
        state=self.state()
        calls=[]
        def step(buttons,**kwargs):
            calls.append(list(buttons));env.frames+=1
            self.assertNotIn('b',buttons)
            if 'right' in buttons:
                self.assertNotIn('a',buttons)
                state['x']=75;m[0xFF9E]=0
            if 'a' in buttons:m[0xC280]=0
        env.step_buttons.side_effect=step
        with patch('gameboy_agent.dungeon_items.snapshot',side_effect=lambda _:dict(state)), \
             patch('gameboy_agent.dungeon_items.mode',return_value='world'):
            clear_map_enemies(env,[],room=21,budget=3)
        self.assertEqual(calls,[['right'],['a'],[]])

    def test_sword_cooldown_is_not_a_blocked_map_walk(self):
        from gameboy_agent.dungeon_items import clear_map_enemies
        env=self.environment();m=env.pyboy.memory
        m[0xC280],m[0xC3A0]=5,25
        m[0xC200],m[0xC210]=67,88;m[0xFF9E]=0
        state=self.state();state['room']=[1,0,20]
        def step(buttons,**kwargs):
            self.assertFalse(set(buttons)&{'up','down','left','right'})
            env.frames+=1
        env.step_buttons.side_effect=step
        with patch('gameboy_agent.dungeon_items.snapshot',return_value=state), \
             patch('gameboy_agent.dungeon_items.mode',return_value='world'):
            with self.assertRaisesRegex(RouteBlocker,'clearance budget'):
                clear_map_enemies(env,[],budget=40)

    def test_falling_enemy_does_not_redirect_navigation_defense(self):
        env=self.environment();m=env.pyboy.memory
        m[0xC280],m[0xC3A0]=2,32
        m[0xC200],m[0xC210]=60,98
        state=self.state();calls=[]
        def step(buttons,**kwargs):
            calls.append(list(buttons));state['x']+=1;env.frames+=1
        env.step_buttons.side_effect=step
        with patch('gameboy_agent.dungeon_items.snapshot',side_effect=lambda _:dict(state)), \
             patch('gameboy_agent.dungeon_items.mode',return_value='world'):
            ItemSteps(env).move(21,'right',lambda s:s['x']>=58,defend=True)
        self.assertEqual(calls,[['right','b'],[]])

    def test_close_stalfos_guard_turns_toward_contact(self):
        from gameboy_agent.dungeon_items import clear_map_enemies
        env=self.environment();m=env.pyboy.memory
        m[0xC280],m[0xC3A0]=5,30
        m[0xC200],m[0xC210]=67,88;m[0xFF9E]=2
        state=self.state();state['room']=[1,0,20];calls=[]
        def step(buttons,**kwargs):
            calls.append(list(buttons));env.frames+=1
            if 'right' in buttons:m[0xFF9E]=0
            if 'a' in buttons:m[0xC280]=0
        env.step_buttons.side_effect=step
        with patch('gameboy_agent.dungeon_items.snapshot',return_value=state), \
             patch('gameboy_agent.dungeon_items.mode',return_value='world'):
            clear_map_enemies(env,[],budget=3)
        self.assertEqual(calls,[['b','right'],['a'],[]])
