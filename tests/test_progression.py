"""Progression contract tests; synthetic RAM fixtures are never gameplay demos."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gameboy_agent.progression import ProgressJournal, snapshot
from gameboy_agent.progression_env import ProgressionEnv, advance_progression
from gameboy_agent.transitions import TransitionTracker, TransitionTimeout
from gameboy_agent.progression_skills import equip_item, InteractionFailure


def state(**updates):
    memory = bytearray(65536)
    for address, value in {0xDB95:11, 0xDB96:7, 0xC16B:4, 0xDB5A:24, 0xDB5B:3}.items():
        memory[address] = value
    s = snapshot(SimpleNamespace(memory=memory))
    s.update(updates)
    return s


class JournalTests(unittest.TestCase):
    def test_initial_success_is_rejected(self):
        for initial in (state(tail_key=1), state(tail_door_status=16), state(room=[1,0,23])):
            with self.assertRaises(ValueError):
                ProgressJournal(initial)

    def test_entry_requires_acquisition_opening_alive_and_settled(self):
        j = ProgressJournal(state())
        entered = state(room=[1,0,23])
        j.observe(entered, frame=1, decision=0, settled=True)
        self.assertNotIn('tail_cave_entered', j.milestones)
        entered.update(tail_key=1, tail_door_status=16)
        j.observe(entered, frame=2, decision=1, settled=False)
        self.assertIn('tail_key_acquired', j.milestones)
        self.assertNotIn('tail_cave_entered', j.milestones)
        j.observe(dict(entered, health=0), frame=3, decision=2, settled=True)
        self.assertNotIn('tail_cave_entered', j.milestones)
        # Separate live sequence for success; do not revive the death fixture.
        j = ProgressJournal(state())
        j.observe(state(tail_key=1), frame=1, decision=0)
        j.observe(state(tail_key=1, tail_door_status=16), frame=2, decision=1)
        j.observe(entered, frame=3, decision=2, settled=True)
        j.observe(entered, frame=4, decision=3, settled=True)
        self.assertEqual(sum(e['kind']=='tail_cave_entered' for e in j.events), 1)

    def test_transient_and_dialogue_entry_cannot_complete(self):
        for phase_update, dialog in [({'subtype':1}, 0), ({}, 1)]:
            j = ProgressJournal(state())
            s = state(tail_key=1, tail_door_status=16, room=[1,0,23], dialog_state=dialog)
            s['phase'].update(phase_update)
            j.observe(s, frame=1, decision=0, settled=True)
            self.assertNotIn('tail_cave_entered', j.milestones)

    def test_frame_damage_and_healing_do_not_cancel(self):
        j = ProgressJournal(state())
        j.observe(state(health=20), frame=1, decision=0)
        j.observe(state(health=24), frame=2, decision=0)
        self.assertEqual((j.damage_raw,j.healing_raw), (4,4))
        self.assertIsNone(j.events[0]['details']['cause'])

    def test_powder_distinguishes_toadstool_and_count(self):
        j = ProgressJournal(state())
        s = state(inventory=[12]+[0]*11, toadstool=1, powder=20)
        j.observe(s, frame=1, decision=0)
        self.assertNotIn('powder_available',j.milestones)
        s.update(toadstool=0, powder=0)
        j.observe(s, frame=2, decision=1)
        self.assertNotIn('powder_available',j.milestones)
        s.update(powder=20)
        j.observe(s, frame=3, decision=2)
        self.assertIn('powder_available',j.milestones)

    def test_swaps_are_not_item_acquisition_and_dialogue_is_not_a_quote(self):
        j = ProgressJournal(state(inventory=[4,0]+[0]*10))
        j.observe(state(inventory=[0,4]+[0]*10,dialog_state=1,dialog_id=0x123),frame=1,decision=0)
        self.assertEqual(j.events[0]['details']['added'], [])
        self.assertEqual(j.events[0]['details']['removed'], [])
        self.assertIsNone(j.events[1]['details']['exact_text'])

    def test_journal_roundtrip_and_directed_room_evidence(self):
        j = ProgressJournal(state())
        j.observe(state(), frame=0, decision=0, settled=True)
        restored = ProgressJournal.restore(json.loads(json.dumps(j.state())))
        for obj in (j,restored):
            obj.observe(state(room=[0,0,1]), frame=10, decision=1, settled=True)
        self.assertEqual(j.state(), restored.state())
        self.assertFalse(j.events[0]['details']['reverse_verified'])

    def test_transition_wait_has_a_bound_and_no_input(self):
        class Boy:
            memory = bytearray(65536)
            frames = 0
            def button_release(self, button): pass
            def button_press(self, button): raise AssertionError('Input during transition')
            def tick(self, n, render): self.frames += n
        boy = Boy(); boy.memory[0xDB5A] = 24
        with self.assertRaises(TransitionTimeout):
            advance_progression(boy, TransitionTracker(), ['right'], max_wait=7)
        self.assertEqual(boy.frames,7)


class LiveInterfaceTests(unittest.TestCase):
    def setUp(self):
        roms = list(ROOT.glob('*.gbc'))
        if len(roms) != 1:
            self.skipTest('Requires local verified ROM')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        rom = Path(self.tmp.name)/'game.gbc';shutil.copy2(roms[0],rom)
        self.env = ProgressionEnv(rom, ROOT/'references/LADXExperiments/ladx.gbc.state',max_steps=100)
        self.addCleanup(self.env.close)
        self.env.reset(seed=0)

    def test_read_only_observations_depleted_powder_duplicates_and_key_one(self):
        env = self.env
        # Explicit synthetic setup; this is not an agent trajectory.
        env.pyboy.memory[0xDB02] = 12
        env.pyboy.memory[0xDB03] = 12
        env.pyboy.memory[0xDB4C] = 1
        env.pyboy.memory[0xDB76] = 20
        env.pyboy.memory[0xDB11] = 1
        real = env.pyboy
        before = bytes(real.memory[0xC000:0xE000])
        class ReadOnlyMemory:
            def __getitem__(self, key): return real.memory[key]
            def __setitem__(self, key, value): raise AssertionError('Observation wrote game memory')
        class ReadOnlyBoy:
            memory = ReadOnlyMemory()
            def __getattr__(self, name): return getattr(real,name)
        env.pyboy = ReadOnlyBoy()
        try:
            for _ in range(100):
                env.get_observation()
                self.assertEqual(env.get_inventory_progress()['TAIL_KEY'],1)
                env.script_give_magic_powder()
                snapshot(env.pyboy)
        finally:
            env.pyboy = real
        self.assertEqual(before,bytes(real.memory[0xC000:0xE000]))
        self.assertEqual(real.memory[0xDB4C],1)
        self.assertEqual(real.memory[0xDB02:0xDB04],[12,12])

    def test_invalid_commands_do_not_advance(self):
        initial = self.env.frames
        for action in ([0,3], [-1,0]):
            with self.assertRaises(ValueError):self.env.step(np.array(action))
        for buttons,frames in [(['start'],10),(['up','down'],1),(['wat'],1)]:
            with self.assertRaises(ValueError):self.env.step_buttons(buttons,action_frames=frames)
        with self.assertRaises(RuntimeError):self.env.switch_inventory()
        self.assertEqual(self.env.frames,initial)
        self.assertEqual(self.env.total_steps,0)

    def test_physical_equipping_and_reset_clear_episode_state(self):
        for buttons in (['start'],[],['b'],[],['a'],[],['start'],[]):
            self.env.step_buttons(buttons,action_frames=1)
        self.assertEqual(self.env.pyboy.memory[0xDB00:0xDB03],[0,4,0])
        self.assertEqual(self.env.last_timing['mode'],'world')
        self.env.reset(seed=0)
        self.assertEqual(self.env.pyboy.memory[0xDB00:0xDB03],[4,0,0])
        self.assertEqual(self.env.journal.events,[])
        self.assertEqual(self.env.episode_actions,[])

    def test_no_powder_grant_even_at_synthetic_witch_location(self):
        before=bytes(self.env.pyboy.memory[0xDB00:0xDB80])
        with patch.object(self.env, 'get_map_pos', return_value=(9,1,12)):
            self.env.script_give_magic_powder()
        self.assertEqual(before,bytes(self.env.pyboy.memory[0xDB00:0xDB80]))

    def test_equip_skill_uses_observed_slots_and_has_missing_item_boundary(self):
        with self.assertRaises(InteractionFailure):
            equip_item(self.env,12)
        self.assertEqual(self.env.total_steps,0)
        result=equip_item(self.env,4,button='a')
        self.assertEqual(result['status'],'succeeded')
        self.assertEqual(self.env.pyboy.memory[0xDB01],4)
        equip_item(self.env,4,button='b')
        self.assertEqual(self.env.pyboy.memory[0xDB00],4)


if __name__ == '__main__':unittest.main()
