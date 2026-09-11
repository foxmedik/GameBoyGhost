import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from terrain_sword import reachable_terrain, approaching, gate, signed

class TerrainSwordTests(unittest.TestCase):
    def state(self):
        return dict(x=64,y=64,facing=1,indoor=0,objects=[0]*128,physics=[0]*256,
                    dialogue=False,sword_button=1,sword_state=0,entities=[])

    def test_geometry_and_input_turn(self):
        # Independently enumerated assembly sample cells at hardware (64,64).
        for movement, index in ((4,52),(3,51),(1,36),(2,68)):
            s=self.state();s['objects'][index]=0x5C
            self.assertEqual(gate([movement,1],**s),([movement,1],'reachable_foliage'))
            s['objects'][index]=0x20
            self.assertEqual(gate([movement,1],**s),([movement,0],'clear_path'))

    def test_map_groups_and_physics(self):
        s=self.state();s['objects'][52]=0xDD
        self.assertEqual(gate([4,1],**s)[1],'clear_path')
        s['indoor']=1
        self.assertEqual(gate([4,1],**s)[1],'reachable_foliage')
        for flag in (1,0x90,0xD0,0xD4):
            s['physics'][0xDD]=flag
            self.assertEqual(gate([4,1],**s)[1],'clear_path')

    def test_no_padding_wrap_or_unreachable_foliage(self):
        s=self.state();s['objects'][53]=0x5C
        self.assertEqual(gate([4,1],**s)[1],'clear_path')
        args={k:s[k] for k in ('x','y','facing','indoor','objects','physics')}
        args.update(x=0,y=16,objects=[0x5C]*128)
        self.assertIsNone(reachable_terrain(**args,movement=3))
        self.assertIsNone(reachable_terrain(**args,movement=1))
        self.assertIsNone(reachable_terrain(**args,movement=0))

    def test_cannot_cut_and_active_swing(self):
        s=self.state();s['objects'][52]=0x5C
        self.assertEqual(gate([4,1],**s,cutting_blocked=True)[1],'clear_path')
        s['sword_state']=3
        self.assertEqual(gate([4,1],**s)[1],'swing_active')

    def test_preserve_dialogue_items_movement_and_exit(self):
        s=self.state();s['dialogue']=True
        self.assertEqual(gate([4,1],**s),([4,1],'unchanged'))
        s['dialogue']=False
        self.assertEqual(gate([4,2],**s),([4,2],'unchanged'))
        s['x']=6
        self.assertEqual(gate([3,1],**s),([3,1],'unseen_exit'))

    def test_signed_motion_closest_approach_and_exclusions(self):
        self.assertEqual(signed(240)/16,-1)
        e=dict(status=5,type=0xC6,x=110,y=64,vx=-1,vy=0)
        self.assertTrue(approaching([e],64,64,0))
        e['vx']=1
        self.assertFalse(approaching([e],64,64,0))
        e.update(vx=-10,x=164)
        self.assertTrue(approaching([e],64,64,0)) # crosses before horizon ends
        e['type']=0x3F
        self.assertFalse(approaching([e],64,64,0))
        e.update(type=0xC6,status=0)
        self.assertFalse(approaching([e],64,64,0))

if __name__=='__main__':unittest.main()
