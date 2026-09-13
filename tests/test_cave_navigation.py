from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from gameboy_agent.cave_navigation import (
    PUSHABLE_BLOCK, PUSH_FRAMES, SWORD_BREAKABLE_CRYSTAL, block_changed,
    breakable_crystals, crystal_cleared, loaded_warps, obstacle_phase,
    push_direction, toadstool_stone_push_plan,
    plan_block_exit,
)


class CaveNavigationTests(unittest.TestCase):
    def test_exit_search_opens_lane_and_never_repushes_a6(self):
        objects = [1]*128
        physics = [1]*256
        physics[0x0D] = 0
        for x in range(1,10):
            objects[3*16+x] = 0x0D
        objects[3*16+7] = 0xA7
        blocked = plan_block_exit(objects,physics,(1,3),max_states=40)
        self.assertEqual(blocked['status'],'no_plan_within_budget')
        for x,y in ((6,4),(7,4),(7,2)):
            objects[y*16+x] = 0x0D
        result = plan_block_exit(objects,physics,(1,3),max_states=40)
        self.assertEqual(result['status'],'planned')
        self.assertEqual(result['pushes'],[dict(index=55,direction=1,
            stance=[7,4],destination_index=39)])

    def test_push_only_accepts_cardinal_adjacent_cells(self):
        self.assertEqual(push_direction((4, 5), (4, 4)), 1)
        self.assertEqual(push_direction((4, 5), (4, 6)), 2)
        self.assertEqual(push_direction((4, 5), (3, 5)), 3)
        self.assertEqual(push_direction((4, 5), (5, 5)), 4)
        self.assertIsNone(push_direction((4, 5), (6, 5)))
        self.assertIsNone(push_direction((4, 5), (5, 4)))

    def test_push_requires_object_grid_change(self):
        before = [0] * 128
        before[0x34] = PUSHABLE_BLOCK
        block = dict(index=0x34)
        self.assertFalse(block_changed(before, before, block))
        after = before.copy()
        after[0x34] = 0
        self.assertTrue(block_changed(before, after, block))

    def test_push_duration_is_source_grounded(self):
        self.assertEqual(PUSH_FRAMES, 64)

    def test_warps_ignore_stale_categories(self):
        class Boy:
            memory = bytearray(0x10000)

        boy = Boy()
        boy.memory[0xD401:0xD406] = bytes((1, 0x10, 0xA7, 80, 124))
        boy.memory[0xD416] = 0x33
        boy.memory[0xD406:0xD40B] = bytes((0xFF, 1, 2, 3, 4))
        self.assertEqual(loaded_warps(boy), [
            dict(index=0, category=1, map=0x10, room=0xA7,
                 destination_x=80, destination_y=124, tile_index=0x33,
                 col=3, row=3),
        ])

    def test_crystals_are_distinct_from_pushable_blocks(self):
        class Boy:
            memory = bytearray(0x10000)

        boy = Boy()
        boy.memory[0xDBA5] = 1
        boy.memory[0xD711 + 0x33] = SWORD_BREAKABLE_CRYSTAL
        boy.memory[0xD711 + 0x44] = PUSHABLE_BLOCK
        self.assertEqual(breakable_crystals(boy), [
            dict(index=0x33, col=3, row=3, object_id=SWORD_BREAKABLE_CRYSTAL),
        ])

    def test_crystal_clear_requires_live_object_change(self):
        before = [0] * 128
        before[0x33] = SWORD_BREAKABLE_CRYSTAL
        crystal = dict(index=0x33)
        self.assertFalse(crystal_cleared(before, before, crystal))
        after = before.copy()
        after[0x33] = 0
        self.assertTrue(crystal_cleared(before, after, crystal))

    def test_crystals_gate_block_planning(self):
        class Boy:
            memory = bytearray(0x10000)

        boy = Boy()
        boy.memory[0xDBA5] = 1
        boy.memory[0xD711 + 0x33] = SWORD_BREAKABLE_CRYSTAL
        boy.memory[0xD711 + 0x44] = PUSHABLE_BLOCK
        self.assertEqual(obstacle_phase(boy)['kind'], 'clear_crystals')
        boy.memory[0xD711 + 0x33] = 0
        self.assertEqual(obstacle_phase(boy)['kind'], 'push_blocks')
        boy.memory[0xD711 + 0x44] = 0
        self.assertEqual(obstacle_phase(boy), dict(kind='navigate', targets=[]))

    def test_toadstool_stone_room_uses_the_verified_two_push_order(self):
        class Boy:
            memory = bytearray(0x10000)

        boy = Boy()
        boy.memory[0xDBA5] = 1
        boy.memory[0xFFF7] = 0x0A
        boy.memory[0xFFF6] = 0xAB
        boy.memory[0xD711 + 0x37] = PUSHABLE_BLOCK
        boy.memory[0xD711 + 0x57] = PUSHABLE_BLOCK
        self.assertEqual(toadstool_stone_push_plan(boy), [
            dict(index=0x37, col=7, row=3, direction=3),
            dict(index=0x57, col=7, row=5, direction=2),
        ])
        boy.memory[0xD711 + 0x37] = 0
        self.assertEqual(toadstool_stone_push_plan(boy), [
            dict(index=0x57, col=7, row=5, direction=2),
        ])


if __name__ == '__main__':
    unittest.main()
