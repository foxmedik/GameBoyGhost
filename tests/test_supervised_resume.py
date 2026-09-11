"""Resume the actual supervised optimizer, not just inference weights."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import numpy as np
import torch
from stable_baselines3 import PPO
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import clone

class SupervisedResume(unittest.TestCase):
    def test_optimizer_suffix_exact_and_corruption_rejected(self):
        source=ROOT/'runs/route-teacher-probe-v2/demonstrations.npz'
        if not source.exists():self.skipTest('Local demonstration fixture required')
        torch.set_num_threads(2)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);full=root/'full';split=root/'split';full.mkdir();split.mkdir()
            data=np.load(source);np.savez_compressed(full/'demonstrations.npz',**{k:data[k][:64] for k in data.files})
            shutil.copy2(full/'demonstrations.npz',split/'demonstrations.npz')
            clone(full,20)
            clone(split,20,stop_after=10)
            clone(split,20,resume=split/'bc-checkpoints/0010')
            left=PPO.load(full/'imitation-policy.zip',device='cpu').policy.state_dict()
            right=PPO.load(split/'imitation-policy.zip',device='cpu').policy.state_dict()
            self.assertTrue(all(torch.equal(left[k],right[k]) for k in left))
            a=torch.load(full/'bc-checkpoints/0020/training-state.pt');b=torch.load(split/'bc-checkpoints/0020/training-state.pt')
            for key,fields in a['optimizer']['state'].items():
                for name,value in fields.items():self.assertTrue(torch.equal(value,b['optimizer']['state'][key][name]))
            self.assertTrue(torch.equal(a['shuffle_rng'],b['shuffle_rng']))
            with (split/'bc-checkpoints/0010/training-state.pt').open('ab') as f:f.write(b'bad')
            with self.assertRaisesRegex(ValueError,'integrity'):
                clone(split,20,resume=split/'bc-checkpoints/0010')
if __name__=='__main__':unittest.main()
