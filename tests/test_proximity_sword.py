import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from proximity_sword import gate

class ProximitySwordTests(unittest.TestCase):
 def apply(self,**kw):
  args=dict(dialogue=False,sword_button=1,sword_state=0,entities=[],x=64,y=64);args.update(kw)
  return gate([4,1],**args)
 def test_no_enemy_suppresses_only_button(self):self.assertEqual(self.apply(),([4,0],'no_near_threat'))
 def test_npc_does_not_trigger_swing(self):self.assertEqual(self.apply(entities=[dict(type=0x3F,status=5,x=65,y=64)])[0],[4,0])
 def test_inactive_enemy_does_not_trigger_swing(self):self.assertEqual(self.apply(entities=[dict(type=0x0B,status=0,x=65,y=64)])[0],[4,0])
 def test_radius_boundary(self):
  self.assertEqual(self.apply(entities=[dict(type=0x0B,status=5,x=96,y=64)])[0],[4,1])
  self.assertEqual(self.apply(entities=[dict(type=0x0B,status=5,x=97,y=64)])[0],[4,0])
 def test_active_swing_releases(self):self.assertEqual(self.apply(sword_state=3,entities=[dict(type=0x0B,status=5,x=65,y=64)]),([4,0],'swing_active'))
 def test_dialogue_and_other_item_are_unchanged(self):
  self.assertEqual(self.apply(dialogue=True),([4,1],'unchanged'))
  self.assertEqual(self.apply(sword_button=2),([4,1],'unchanged'))
if __name__=='__main__':unittest.main()
