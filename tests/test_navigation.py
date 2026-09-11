"""Navigation goal semantics and exact optimizer resume on a small dataset."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from gameboy_agent.navigation import reached,encode
try:
    from gameboy_agent.dataset import sha256
    from train_navigation import fit,sampled_steps
except ModuleNotFoundError:
    raise unittest.SkipTest('Optional navigation data dependencies not installed')


class NavigationTest(unittest.TestCase):
    def test_sampling_does_not_alias_alternating_buttons(self):
        offsets=[step for i in range(64) for step in sampled_steps(dict(segment_id=str(i),step_start=0,step_end=32))]
        self.assertEqual(len(offsets),512)
        self.assertEqual({x%2 for x in offsets},{0,1})
        self.assertTrue(all(0<=x<32 for x in offsets))

    def test_goal_requires_correct_room_and_pixel_tolerance(self):
        goal=dict(room=[0,0,242],x=80,y=80)
        self.assertTrue(reached([0,0,242],84,84,goal))
        self.assertFalse(reached([0,0,241],80,80,goal))
        self.assertFalse(reached([0,0,242],85,84,goal))

    def test_goal_changes_input_without_mutating_observation(self):
        obs=dict(control=np.zeros(5,np.float32),vector=np.zeros(89,np.float32),entity_type=np.zeros(16,np.int32),
                 entity_info=np.zeros((16,4),np.float32),minimap_object=np.zeros((11,11),np.uint8),minimap_info=np.zeros((11,11,10),np.float32))
        a=encode(obs,[0,0,242],[0,0,242],40,50);b=encode(obs,[0,0,242],[0,0,226],70,30)
        self.assertFalse(np.array_equal(a,b));self.assertTrue(np.isfinite(a).all())
        self.assertTrue(all(np.count_nonzero(v)==0 for v in obs.values()))

    def test_epoch_resume_matches_uninterrupted_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cache=root/'cache';cache.mkdir();rng=np.random.default_rng(17)
            for split,n in [('train',64),('dev',32)]:
                np.save(cache/f'{split}-x.npy',rng.normal(size=(n,16)).astype(np.float32))
                np.save(cache/f'{split}-y.npy',np.stack([rng.integers(0,5,n),rng.integers(0,3,n)],axis=1))
            (cache/'manifest.json').write_text(json.dumps({'artifacts':{p.name:sha256(p) for p in cache.iterdir()}}))
            full,full_optimizer,_=fit(cache,root/'full',epochs=4)
            fit(cache,root/'split',epochs=4,stop_after=2)
            resumed,resumed_optimizer,_=fit(cache,root/'split',epochs=4,resume=root/'split/epoch-002.pt')
            for name,value in full.state_dict().items():self.assertTrue(torch.equal(value,resumed.state_dict()[name]),name)
            for key,state in full_optimizer.state_dict()['state'].items():
                for name,value in state.items():
                    other=resumed_optimizer.state_dict()['state'][key][name]
                    if torch.is_tensor(value):self.assertTrue(torch.equal(value,other))
                    else:self.assertEqual(value,other)
            checkpoint=root/'split/epoch-002.pt'
            with checkpoint.open('ab') as stream:stream.write(b'corrupt')
            with self.assertRaisesRegex(ValueError,'integrity mismatch'):
                fit(cache,root/'rejected',epochs=4,resume=checkpoint)


if __name__=='__main__':unittest.main()
