"""Suffix selection removes conflicting loop labels with source provenance."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
try:
    from fix_navigation_regression import shortest_labels
    from gameboy_agent.dataset import sha256
except ModuleNotFoundError:
    raise unittest.SkipTest('Optional navigation data dependencies not installed')


class FocusedLabelTest(unittest.TestCase):
    def test_shorter_suffix_wins_after_history_masking(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'success-0.npz'
            x=np.array([[1,2,3,1],[1,2,3,2],[8,7,6,3]],dtype=np.float32)
            y=np.array([[1,0],[2,1],[3,0]],dtype=np.int64)
            np.savez(p,x=x,y=y)
            (p.parent/'manifest.json').write_text(json.dumps(dict(replay_verified=True,artifacts={p.name:sha256(p)},successes=[dict(attempt=0,actions=y.tolist())],attempts=[dict(attempt=0,success=True,damage=0)])))
            xx,yy,provenance,conflicts=shortest_labels([p],np.array([1,1,1,0],dtype=np.float32))
            self.assertEqual(conflicts,1);self.assertEqual(len(xx),2)
            self.assertEqual(yy[0].tolist(),[2,1]);self.assertEqual(provenance[0]['row'],1)
            with p.open('ab') as f:f.write(b'corrupt')
            with self.assertRaises(AssertionError):shortest_labels([p],np.ones(4))

if __name__=='__main__':unittest.main()
