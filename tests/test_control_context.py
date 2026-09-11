"""Controller context adds read-only sensing and action history."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from gameboy_agent.training_env import TrainingEnv
from control_context import ControlContext

class ContextTest(unittest.TestCase):
    def test_observation_is_pure_and_actions_keep_same_clock(self):
        roms=list(ROOT.glob('*.gbc'))
        if len(roms)!=1:self.skipTest('Local ROM required')
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'game.gbc';shutil.copy2(roms[0],target)
            base=TrainingEnv(target,ROOT/'references/LADXExperiments/ladx.gbc.state',max_steps=20)
            env=ControlContext(base)
            try:
                obs,_=env.reset(seed=0)
                before=bytes(base.pyboy.memory[0xC000:0xE000])
                self.assertTrue(env.observation_space.contains(obs))
                for _ in range(3):env.observation(base.cached_observation)
                self.assertEqual(before,bytes(base.pyboy.memory[0xC000:0xE000]))
                obs,_,_,_,info=env.step(np.array([3,2]))
                self.assertEqual(info['action_frames'],10)
                np.testing.assert_allclose(obs['control'][-2:],[.75,2/3])
                obs,_=env.reset(seed=0)
                np.testing.assert_array_equal(obs['control'][-2:],[0,0])
            finally:env.close()
if __name__=='__main__':unittest.main()
