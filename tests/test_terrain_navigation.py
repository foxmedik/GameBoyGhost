"""Conservative collision routing, regional memory and narrow-lane steering."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.terrain_navigation import paths,component,exits,choose_exit,steer,cell


class TerrainNavigationTests(unittest.TestCase):
    def test_wall_ledge_pit_and_uncertain_tiles_are_not_paths(self):
        for flag in (1,0x10,0x30,0x50,0x80,0x90):
            grid=[[1]*10 for _ in range(8)];grid[4][3]=0;grid[4][4]=flag;grid[4][5]=0
            self.assertNotIn((5,4),paths(grid,(3,4)))

    def test_stairs_connect_separated_levels(self):
        grid=[[0]*10 for _ in range(8)];grid[3]=[1]*10;grid[3][8]=2
        self.assertIn((2,1),paths(grid,(2,6)))
        self.assertIn((8,3),paths(grid,(2,6))[(2,1)])

    def test_same_room_can_have_distinct_reachable_regions(self):
        grid=[[0]*10 for _ in range(8)];grid[3]=[1]*10
        self.assertNotEqual(component(grid,(2,1)),component(grid,(2,6)))

    def test_north_wall_cannot_become_a_candidate_exit(self):
        grid=[[0]*10 for _ in range(8)];grid[0]=[1]*10
        self.assertFalse(any(e['direction']==1 for e in exits(grid,(3,4),0xE1)))

    def test_world_edges_do_not_wrap(self):
        grid=[[0]*10 for _ in range(8)]
        candidates=exits(grid,(3,4),0)
        self.assertFalse(any(e['direction'] in (1,3) for e in candidates))

    def test_narrow_corridor_centres_x_before_forward_motion(self):
        self.assertEqual(steer(106,127,(6,7)),3)
        self.assertEqual(steer(103,127,(6,7)),1)
        self.assertIsNone(steer(103,124,(6,7)))
        self.assertEqual(cell(106,127),(6,7))

    def test_choice_is_deterministic_and_respects_rejected_exit(self):
        grid=[[0]*10 for _ in range(8)]
        first=choose_exit(grid,(5,5),0x90,0x50,{},set())
        self.assertEqual(first,choose_exit(grid,(5,5),0x90,0x50,{},set()))
        rejected={(0x90,first['direction'],tuple(first['cell']))}
        self.assertNotEqual(first,choose_exit(grid,(5,5),0x90,0x50,{},rejected))


if __name__=='__main__':unittest.main()
