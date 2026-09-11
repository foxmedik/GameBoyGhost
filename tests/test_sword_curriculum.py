import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from build_sword_curriculum import build
from gameboy_agent.training_env import TrainingEnv

class SwordCurriculum(unittest.TestCase):
    def test_scripted_start_requires_play_and_success_is_not_death(self):
        if len(list(ROOT.glob('*.gbc'))) != 1:self.skipTest('Local ROM required')
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);manifest=build(directory/'starts')
            self.assertEqual(len(manifest['stages']),2)
            rom=directory/'game.gbc';shutil.copy2(next(ROOT.glob('*.gbc')),rom)
            initial=directory/'starts/sword_approach.state'
            env=TrainingEnv(rom,initial,max_steps=2048,sword_curriculum=True)
            try:
                env.reset(seed=0)
                for _ in range(100):
                    _,reward,done,_,info=env.step(np.array([0,0]))
                    self.assertFalse(done)
                    self.assertFalse(info['sword_acquired'])
                    self.assertAlmostEqual(reward,-0.001)
                env.reset(seed=0)
                # Exact physical fixture suffix proves the goal is reachable.
                with initial.open('rb') as f:env.pyboy.load_state(f)
                sequence=json.loads((ROOT/'configs/fixtures/house_to_sword_and_push.json').read_text())
                for segment in sequence[142:161]:
                    for button in ('up','down','left','right','a','b','start','select'):
                        (env.pyboy.button_press if button in segment['buttons'] else env.pyboy.button_release)(button)
                    env.pyboy.tick(segment['frames'],render=True)
                _,reward,done,_,info=env.step(np.array([0,0]))
                self.assertTrue(done)
                self.assertTrue(info['sword_acquired'])
                self.assertFalse(info['death'])
                self.assertEqual(reward,10.0)
                with self.assertRaises(RuntimeError):env.step(np.array([0,0]))
            finally:env.close()

if __name__=='__main__':unittest.main()
