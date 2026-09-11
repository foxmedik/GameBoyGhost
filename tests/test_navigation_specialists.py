import tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from gameboy_agent.navigation import NavigationNet,NavigationController

class NavigationSpecialistsTests(unittest.TestCase):
 def saved(self,move,button):
  m=NavigationNet(250)
  with torch.no_grad():
   for p in m.parameters():p.zero_()
   m.net[4].bias[move]=1;m.net[4].bias[5+button]=1
  return m.state_dict()
 def test_self_contained_dispatch_matches_entire_final_goal(self):
  g=dict(room=[0,0,226],x=64,y=64);parent=self.saved(4,1)
  s=dict(inputs=250,model=parent,mean=np.zeros(250,dtype=np.float32),scale=np.ones(250,dtype=np.float32),input_mask=np.ones(250,dtype=np.float32),goal_experts=[dict(goal=g,model=self.saved(3,0))])
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'policy.pt';torch.save(s,p);c=NavigationController(p)
   with patch('gameboy_agent.navigation.encode',return_value=np.zeros(250,dtype=np.float32)):
    self.assertEqual(c.action({},[0,0,225],g),[3,0])
    for goal in [dict(g,x=65),dict(g,y=65),dict(g,room=[0,1,226]),dict(g,room=[1,0,226]),dict(g,room=[0,0,225])]:self.assertEqual(c.action({},[0,0,226],goal),[4,1])
   self.assertTrue(all(torch.equal(parent[k],c.model.state_dict()[k]) for k in parent))
 def test_legacy_checkpoint_has_no_specialists(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'policy.pt';torch.save(dict(inputs=250,model=self.saved(1,2),mean=np.zeros(250,dtype=np.float32),scale=np.ones(250,dtype=np.float32)),p);c=NavigationController(p)
   self.assertEqual(c.goal_experts,{})
   with patch('gameboy_agent.navigation.encode',return_value=np.zeros(250,dtype=np.float32)):self.assertEqual(c.action({},[0,0,0],dict(room=[0,0,226],x=64,y=64)),[1,2])
if __name__=='__main__':unittest.main()
