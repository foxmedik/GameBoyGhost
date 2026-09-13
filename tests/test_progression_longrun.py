"""Frozen panels must vary physical inputs and keep validation separate."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


@unittest.skip("Historical reserved-panel generation is sealed; do not reconstruct its cases")
class PanelTests(unittest.TestCase):
    def test_disjoint_deterministic_bounded_physical_panels(self):
        import run_progression_longrun as longrun
        plan=longrun.make_plan(3600)
        self.assertEqual(plan['cases'],longrun.make_plan(3600)['cases'])
        specs=plan['cases']
        self.assertEqual(len({s['id'] for s in specs}),len(specs))
        key=lambda s:(s['idle'],s['direction'],s['move_frames'])
        development={key(s) for s in specs if s['split']=='development'}
        validation={key(s) for s in specs if s['split']=='validation'}
        self.assertEqual(len(development),20)
        self.assertEqual(len(validation),20)
        self.assertFalse(development & validation)
        self.assertEqual(len([s for s in specs if s['split']=='development_probe']),720)
        for s in specs:
            self.assertTrue(0<=s['idle']<=600)
            self.assertTrue(0<=s['move_frames']<=6)
            if s['direction']: self.assertGreater(s['move_frames'],0)
        self.assertEqual(plan['optimizer_updates'],0)


if __name__=='__main__':unittest.main()
