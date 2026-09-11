"""Learned tree boundary and action-space regression tests."""
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from tree_controller import fit_tree,predict,features

class TreeControllerTest(unittest.TestCase):
    def test_learns_both_sides_of_control_boundary(self):
        x=np.array([[0,0],[.1,0],[.2,0],[.8,0],[.9,0],[1,0]],dtype=np.float32)
        y=np.array([8,8,8,16,16,16])
        tree=fit_tree(x,y)
        np.testing.assert_array_equal(predict(tree,np.array([.15,0])),[2,0])
        np.testing.assert_array_equal(predict(tree,np.array([.85,0])),[4,0])
    def test_batch_and_single_features_match(self):
        obs={'control':np.arange(5,dtype=np.float32),'vector':np.arange(89,dtype=np.float32),
             'entity_type':np.arange(16,dtype=np.int32),'entity_info':np.arange(64,dtype=np.float32).reshape(16,4)}
        single=features(obs);batch=features({k:np.stack([v,v]) for k,v in obs.items()})
        self.assertEqual(single.shape,(89,));np.testing.assert_array_equal(single,batch[0])
if __name__=='__main__':unittest.main()
