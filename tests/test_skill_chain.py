"""Skill failure boundaries and live continuation/replay across acquisition."""
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from gameboy_agent.skills import Explorer, Senses, SequentialPlanner
from run_skill_chain import run


class ConstantController:
    def action(self, senses):
        return [2, 0]


STATE = Senses((0, 0, 242), 80, 80, False, False, 24, 1, 4)


class SkillTest(unittest.TestCase):
    def test_timeout_and_death_do_not_advance_planner(self):
        planner = SequentialPlanner(ConstantController(), sword_budget=1)
        self.assertEqual(planner.action(STATE, 0), [2, 0])
        self.assertIsNone(planner.action(STATE, 1))
        self.assertEqual(planner.index, 0)
        self.assertEqual(planner.events[-1]['status'], 'budget_exhausted')
        planner = SequentialPlanner(ConstantController())
        self.assertIsNone(planner.action(replace(STATE, sword=True, health=0), 0))
        self.assertEqual(planner.events[-1]['status'], 'failed_death')

    def test_success_handoff_and_exploration_budget(self):
        planner = SequentialPlanner(ConstantController(), explore_budget=1)
        planner.action(replace(STATE, sword=True), 0)
        self.assertEqual(planner.index, 1)
        self.assertEqual(planner.events[0]['status'], 'succeeded')
        self.assertIsNone(planner.action(replace(STATE, sword=True), 1))
        self.assertEqual(planner.events[-1]['status'], 'budget_exhausted')

    def test_blocked_motion_breaks_commitment_and_state_roundtrips(self):
        explorer = Explorer()
        first = explorer.action(STATE)
        for _ in range(3):
            last = explorer.action(STATE)
        self.assertNotEqual(first[0], last[0])
        restored = Explorer(**json.loads(json.dumps(explorer.state())))
        for x in (82, 88, 96):
            state = replace(STATE, x=x)
            self.assertEqual(explorer.action(state), restored.action(state))
        self.assertEqual(explorer.state(), restored.state())

    def test_damage_interrupts_motion_and_records_hazard(self):
        explorer = Explorer()
        first = explorer.action(STATE)
        hurt = replace(STATE, y=78, health=20)
        escape = explorer.action(hurt)
        self.assertEqual(escape[0], {1: 2, 2: 1, 3: 4, 4: 3}[first[0]])
        self.assertEqual(explorer.hazards[hurt.cell], 1)

    def test_live_handoff_and_resume_on_both_sides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full = run(root / 'full', explore_steps=64)
            run(root / 'before', explore_steps=64, stop_after=200)
            resumed_before = run(root / 'after', resume=root / 'before', stop_after=430)
            self.assertEqual(resumed_before['planner']['index'], 1)
            resumed = run(root / 'resumed', resume=root / 'after')
            self.assertTrue(full['sword_acquired'])
            self.assertEqual(full['planner']['events'][0]['step'], 412)
            self.assertEqual(full['steps'], 476)
            self.assertEqual(full['status'], 'budget_exhausted')
            for key in ('actions', 'fingerprint', 'planner', 'rooms', 'post_sword_rooms'):
                self.assertEqual(full[key], resumed[key], key)
            self.assertFalse(full['completion_evaluated'])
            with (root / 'before' / 'policy.json').open('a') as stream:
                stream.write(' ')
            with self.assertRaisesRegex(ValueError, 'artifact mismatch'):
                run(root / 'corrupt', resume=root / 'before')
            self.assertFalse((root / 'corrupt').exists())


if __name__ == '__main__':
    unittest.main()
