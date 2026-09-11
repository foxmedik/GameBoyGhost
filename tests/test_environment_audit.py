"""Integration regressions against the local ROM and pinned upstream savestate.

Fixture RAM edits below are test setup only; they are not agent trajectories.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gameboy_agent.ladx_baseline import BaselineEnv, UPSTREAM
from gameboy_agent.neutral_env import NeutralEnv
from gym_env.memory import RamAddress
from gameboy_agent.rom_profile import validate_rom
sys.path.insert(0, str(ROOT/'scripts'))
from capture_ladx_fixtures import capture


class EnvironmentAudit(unittest.TestCase):
    def setUp(self):
        roms = list(ROOT.glob('*.gbc'))
        if len(roms) != 1:
            self.skipTest('Requires exactly one local GBC ROM')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.rom = Path(self.tmp.name) / 'game.gbc'
        shutil.copy2(roms[0], self.rom)
        self.state = UPSTREAM / 'ladx.gbc.state'

    def env(self, cls=BaselineEnv, **kwargs):
        env = cls(self.rom, self.state, **kwargs)
        self.addCleanup(env.close)
        env.reset(seed=7)
        return env

    def test_reproduction_reward_components_sum_to_scalar(self):
        env = self.env()
        for _ in range(8):
            _, reward, _, _, info = env.step(np.array([0, 0]))
            self.assertAlmostEqual(reward, sum(info['reward'].values()))

    def test_rom_revision_mismatch_is_rejected(self):
        data=bytearray(self.rom.read_bytes())
        data[0x14C] ^= 1
        self.rom.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'Unsupported ROM'):
            validate_rom(self.rom)

    def test_hook_registration_failure_is_not_suppressed(self):
        env = self.env()
        # A hook claimed by another owner must fail instead of silently claiming
        # that instrumentation is active (as the upstream helper does).
        env.pyboy.hook_register(2, 0x729F, lambda _: None, None)
        try:
            with self.assertRaises(ValueError):
                env.register_collision()
            self.assertFalse(env.collided_object_registered)
        finally:
            env.pyboy.hook_deregister(2, 0x729F)

    def test_push_hook_lifecycle_during_repeated_real_hits(self):
        env = self.env()
        # Restore the exact fixture origin without the environment reset ticks.
        with self.state.open('rb') as source:
            env.pyboy.load_state(source)
        sequence=json.loads((ROOT/'configs/fixtures/house_to_sword_and_push.json').read_text())
        from capture_ladx_fixtures import BUTTONS
        hits=0
        for segment in sequence:
            for button in BUTTONS:
                (env.pyboy.button_press if button in segment['buttons'] else env.pyboy.button_release)(button)
            for _ in range(segment['frames']):
                env.push_sfx=False
                env.register_push_sfx()
                env.pyboy.tick(1,render=True)
                # Registration must survive callbacks until tick returns.
                self.assertTrue(env.push_sfx_registered)
                hits += bool(env.push_sfx)
                env.deregister_push_sfx()
                self.assertFalse(env.push_sfx_registered)
        self.assertGreater(hits,100)
        self.assertEqual(list(env.pyboy.memory[0xDB00:0xDB0C]),[4,1]+[0]*10)

    def test_real_transitions_and_projectile_combat_replay(self):
        sequence=json.loads((ROOT/'configs/fixtures/house_to_projectile_combat.json').read_text())
        expected=json.loads((ROOT/'configs/fixtures/house_to_projectile_combat.expected.json').read_text())
        out=Path(self.tmp.name)
        first=capture(sequence,out/'first')
        second=capture(sequence,out/'second')
        unhooked=capture(sequence,out/'unhooked',hooks=False)
        self.assertEqual(first,second)
        self.assertEqual(hashlib.sha256(json.dumps(first,sort_keys=True).encode()).hexdigest(),expected['trace_sha256'])
        self.assertEqual(len(first),expected['frames'])
        for hooked, plain in zip(first,unhooked):
            self.assertEqual({k:v for k,v in hooked.items() if k!='hooks'},
                             {k:v for k,v in plain.items() if k!='hooks'})
        self.assertEqual([r['frame'] for r in first if r['hooks'].get('shield')],expected['shield_frames'])

    def test_sword_pickup_push_and_sword_hit_are_replayable(self):
        sequence=json.loads((ROOT/'configs/fixtures/house_to_sword_and_push.json').read_text())
        expected=json.loads((ROOT/'configs/fixtures/house_to_sword_and_push.expected.json').read_text())
        out=Path(self.tmp.name)
        first=capture(sequence,out/'first')
        replay=capture(sequence,out/'replay')
        plain=capture(sequence,out/'plain',hooks=False)
        self.assertEqual(first,replay)
        self.assertEqual(len(first),len(plain))
        self.assertEqual(hashlib.sha256(json.dumps(first,sort_keys=True).encode()).hexdigest(),expected['trace_sha256'])
        for a,b in zip(first,plain):
            self.assertEqual({k:v for k,v in a.items() if k!='hooks'},
                             {k:v for k,v in b.items() if k!='hooks'})
        self.assertEqual(first[-1]['inventory'],expected['final_inventory'])
        for name,count in expected['hook_counts'].items():
            self.assertGreater(count,0)
            self.assertEqual(sum(row['hooks'].get(name,0) for row in first),count)

    def test_timeout_is_not_death_or_completion(self):
        for cls, action in [(BaselineEnv, np.zeros(2, dtype=int)),
                            (NeutralEnv, np.zeros(8, dtype=np.int8))]:
            with self.subTest(mode=cls.__name__):
                env = self.env(cls, max_steps=1)
                _, _, terminated, truncated, info = env.step(action)
                self.assertFalse(terminated)
                self.assertTrue(truncated)
                self.assertIsNone(info['completion'])
                with self.assertRaises(RuntimeError):
                    env.step(action)

    def test_reproduction_zero_health_is_death(self):
        env = self.env()
        env.pyboy.memory[0xDB5A] = 0
        # Freeze emulation to isolate the termination contract from game logic.
        with patch.object(env, 'run_action_on_emulator'):
            _, _, terminated, truncated, _ = env.step(np.array([0, 0]))
        self.assertTrue(terminated)
        self.assertFalse(truncated)

    def test_invalid_actions_and_failures_propagate(self):
        env = self.env()
        with self.assertRaises(ValueError):
            env.step(np.array([5, 0]))
        with patch.object(env, 'run_action_on_emulator', side_effect=RuntimeError('fixture failure')):
            with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
                env.step(np.array([0, 0]))

    def test_toadstool_observation_is_valid(self):
        env = self.env()
        RamAddress.wHasToadstool.write_memory(env.pyboy, 1)
        obs = env.get_observation()
        self.assertEqual(obs['vector'][12], -0.5)
        self.assertTrue(env.observation_space.contains(obs))

    def test_upstream_observation_refills_powder(self):
        env = self.env()
        env.pyboy.memory[0xDB02] = 0x0C
        RamAddress.wHasToadstool.write_memory(env.pyboy, 0)
        RamAddress.wMagicPowderCount.write_memory(env.pyboy, 1)
        RamAddress.wMaxMagicPowder.write_memory(env.pyboy, 20)
        env.get_observation()
        self.assertEqual(RamAddress.wMagicPowderCount.read_memory(env.pyboy), 20)

    def test_upstream_script_grants_powder(self):
        env = self.env()
        for address in range(0xDB00, 0xDB0C):
            env.pyboy.memory[address] = 0
        with patch.object(env, 'get_map_pos', return_value=(9, 1, 12)):
            env.script_give_magic_powder()
        self.assertIn(0x0C, env.pyboy.memory[0xDB00:0xDB0C])

    def test_neutral_observation_does_not_mutate_work_ram(self):
        env = self.env(NeutralEnv)
        env.pyboy.memory[0xDB02] = 0x0C
        RamAddress.wHasToadstool.write_memory(env.pyboy, 0)
        RamAddress.wMagicPowderCount.write_memory(env.pyboy, 1)
        RamAddress.wMaxMagicPowder.write_memory(env.pyboy, 20)
        before = bytes(env.pyboy.memory[0xC000:0xE000])
        first = env.render()
        first[:] = 0  # Returned framebuffer must not alias emulator memory.
        env.render()
        self.assertEqual(before, bytes(env.pyboy.memory[0xC000:0xE000]))

    def test_neutral_reset_replays_buttons_and_clears_step_counter(self):
        env = self.env(NeutralEnv)
        actions = np.random.default_rng(19).integers(0, 2, (16, 8), dtype=np.int8)
        traces = []
        for _ in range(2):
            obs, _ = env.reset(seed=7)
            self.assertEqual(env.steps, 0)
            trace = [hashlib.sha256(obs.tobytes()).hexdigest()]
            for action in actions:
                obs, reward, terminated, truncated, info = env.step(action)
                self.assertEqual(reward, 0)
                self.assertFalse(terminated)
                self.assertEqual(info['frames_advanced'], 10)
                trace.append(hashlib.sha256(obs.tobytes()+bytes(env.pyboy.memory[0xC000:0xE000])).hexdigest())
            traces.append(trace)
        self.assertEqual(*traces)

    def test_neutral_transition_bytes_do_not_change_frame_budget(self):
        env = self.env(NeutralEnv)
        # Actual transitions still need gameplay fixtures. This tests that the
        # control surface does not inspect transition flags to skip frames.
        for room, warp in [(0, 4), (1, 0), (2, 3)]:
            env.pyboy.memory[0xC124] = room
            env.pyboy.memory[0xC16B] = warp
            before = env.pyboy.frame_count
            env.step(np.zeros(8, dtype=np.int8))
            self.assertEqual(env.pyboy.frame_count-before, 10)


if __name__ == '__main__':
    unittest.main()
