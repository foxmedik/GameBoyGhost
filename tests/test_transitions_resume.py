import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from gameboy_agent.training_env import TrainingEnv
from gameboy_agent.ladx_baseline import CustomFeatureExtractor
from gameboy_agent.transitions import TransitionTracker, world_ready, advance, TransitionTimeout
from gameboy_agent.checkpoint import save_checkpoint, restore_checkpoint, fingerprint


class TransitionsAndResume(unittest.TestCase):
    def setUp(self):
        roms = list(ROOT.glob('*.gbc'))
        if len(roms) != 1:
            self.skipTest('Local ROM required')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rom = self.root/'game.gbc'
        shutil.copy2(roms[0],self.rom)
        self.env = TrainingEnv(self.rom, ROOT/'references/LADXExperiments/ladx.gbc.state',max_steps=256)
        self.addCleanup(self.env.close)
        torch.set_num_threads(1)

    def test_real_house_exit_and_scroll_keep_full_action_budget(self):
        self.env.reset(seed=0)
        transitions=[]
        for action in [[2,0]]*3+[[3,0]]*3+[[2,0]]*12:
            obs,_,_,_,info=self.env.step(np.array(action))
            self.assertTrue(world_ready(info['phase']))
            self.assertEqual(info['action_frames'],10)
            self.assertEqual(info['stable_room'],info['phase']['room'])
            if info['wait_frames']:
                transitions.append(info['phase']['room'])
        self.assertEqual(transitions,[(0,0,0xA2),(0,0,0xB2)])

    def test_transient_idle_gap_does_not_commit_room(self):
        tracker=TransitionTracker()
        ready={'gameplay':11,'subtype':7,'scroll':0,'sequence':4,'palette':0,'room':(0,0,1),'health':24}
        for _ in range(8):tracker.observe(ready)
        blocked=dict(ready,subtype=1,room=(0,0,2))
        tracker.observe(blocked)
        for _ in range(6):
            self.assertFalse(tracker.observe(dict(ready,room=(0,0,2))))
        self.assertEqual(tracker.committed_room,(0,0,1))
        tracker.observe(blocked)
        for _ in range(8):tracker.observe(dict(ready,room=(0,0,2)))
        self.assertEqual(tracker.committed_room,(0,0,2))

    def test_world_map_accepts_policy_buttons_and_exits(self):
        from gameboy_agent.transitions import map_ready
        self.env.reset(seed=0)
        for action in [[2,0]]*3+[[3,0]]*3+[[2,0]]*5:
            self.env.step(np.array(action))
        self.env.pyboy.button_press('select')
        for _ in range(30):
            self.env.pyboy.tick(1,render=True)
            if self.env.pyboy.memory[0xDB95] == 7:break
        self.assertEqual(self.env.pyboy.memory[0xDB95],7)
        self.env.pyboy.button_release('select')
        info=advance(self.env.pyboy,self.env.transition_tracker,[])
        self.assertTrue(map_ready(info['phase']))
        info=advance(self.env.pyboy,self.env.transition_tracker,['b'])
        self.assertTrue(world_ready(info['phase']))
        self.assertEqual(info['action_frames'],10)

    def test_wait_is_bounded(self):
        class FrozenBoy:
            memory={0xDB95:11,0xDB96:1,0xC124:0,0xC16B:0,0xDDD5:0,
                    0xDBA5:0,0xFFF7:0,0xFFF6:1,0xDB5A:24}
            frames=0
            def button_release(self,_):pass
            def button_press(self,_):raise AssertionError('No input during load')
            def tick(self,count,render):self.frames+=count
        boy=FrozenBoy()
        with self.assertRaises(TransitionTimeout):
            advance(boy,TransitionTracker(),['right'],max_wait=12)
        self.assertEqual(boy.frames,12)

    def test_checkpoint_continuation_matches_uninterrupted_optimizer(self):
        vec=DummyVecEnv([lambda:self.env])
        model=PPO('MultiInputPolicy',vec,seed=11,device='cpu',n_steps=32,batch_size=16,n_epochs=2,
                  policy_kwargs={'features_extractor_class':CustomFeatureExtractor,'net_arch':[64]},verbose=0)
        model.learn(64)
        directory=self.root/'checkpoint'
        position={'trajectory_next_index':64,'episode_id':'test-episode',
                  'curriculum':{'kind':'fixed_savestate'},'planner':None,
                  'target_timesteps':320}
        save_checkpoint(directory,model,self.env,experiment_state=position)
        model.learn(256,reset_num_timesteps=False)
        reference_fingerprint=fingerprint(self.env)
        reference={k:v.clone() for k,v in model.policy.state_dict().items()}
        reloaded,env,state=restore_checkpoint(directory,self.rom)
        self.addCleanup(env.close)
        self.assertEqual(state,position)
        reloaded.learn(256,reset_num_timesteps=False)
        self.assertEqual(reference_fingerprint,fingerprint(env))
        self.assertEqual(model.num_timesteps,reloaded.num_timesteps)
        for key,value in reference.items():
            self.assertTrue(torch.equal(value,reloaded.policy.state_dict()[key]),key)
        for key,value in model.policy.optimizer.state_dict()['state'].items():
            for field,expected in value.items():
                actual=reloaded.policy.optimizer.state_dict()['state'][key][field]
                if torch.is_tensor(expected):self.assertTrue(torch.equal(expected,actual))
                else:self.assertEqual(expected,actual)
        # Tampering fails before deserializing trusted local artifacts.
        with (directory/'environment.pkl').open('ab') as f:f.write(b'changed')
        with self.assertRaisesRegex(ValueError,'integrity'):
            restore_checkpoint(directory,self.rom)


if __name__=='__main__':unittest.main()
