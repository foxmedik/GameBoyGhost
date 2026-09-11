"""Goal selection, evidence use, failure bounds and deterministic continuation."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.progression_planner import ProgressionPlanner
from gameboy_agent.world_memory import WorldMemory
from gameboy_agent.skills import Senses


class Policy:
    def action(self,obs,room,goal):
        self.goal=deepcopy(goal)
        return [1,0]


STATE=Senses((0,0,226),36,121,False,True,24,1,4)
GOAL=dict(room=[0,0,226],x=64,y=64)


class PlannerTests(unittest.TestCase):
    def test_goal_is_local_and_no_reverse_edge_is_invented(self):
        policy=Policy();p=ProgressionPlanner(WorldMemory(),[GOAL])
        self.assertEqual(p.action({},STATE,policy),[1,0])
        self.assertEqual(policy.goal,GOAL)
        self.assertIsNone(p.last_decision['memory_evidence'])
        self.assertEqual(p.memory.connections(),[])

    def test_reached_goal_advances_but_prefix_is_not_quest_success(self):
        p=ProgressionPlanner(WorldMemory(),[GOAL])
        self.assertIsNone(p.action({},replace(STATE,x=64,y=64),Policy()))
        self.assertEqual(p.status,'guidance_prefix_complete')
        self.assertEqual(p.events[0]['kind'],'guidance_goal_reached')

    def test_death_and_dialogue_budget_stop_without_navigation(self):
        p=ProgressionPlanner(WorldMemory(),[GOAL],goal_budget=2)
        s=replace(STATE,dialogue=True)
        self.assertEqual(p.action({},s,Policy()),[0,1])
        self.assertEqual(p.action({},s,Policy()),[0,0])
        self.assertIsNone(p.action({},s,Policy()))
        self.assertEqual(p.status,'dialogue_timeout')
        p=ProgressionPlanner(WorldMemory(),[GOAL])
        self.assertIsNone(p.action({},replace(STATE,health=0),Policy()))
        self.assertEqual(p.status,'death')

    def test_stall_recovery_is_bounded_and_roundtrip_preserves_decisions(self):
        p=ProgressionPlanner(WorldMemory(),[GOAL])
        for _ in range(65):p.action({},STATE,Policy())
        other=ProgressionPlanner(WorldMemory(),[GOAL]);other.restore(json.loads(json.dumps(p.state())))
        for _ in range(200):
            a=p.action({},STATE,Policy());b=other.action({},STATE,Policy())
            self.assertEqual(a,b)
            self.assertEqual(p.state(),other.state())
            if a is None:break
        self.assertEqual(p.status,'repeated_local_stall')
        self.assertEqual(p.recoveries,2)
        self.assertLessEqual(p.leg_steps,256)

    def test_shielded_crossing_aligns_lane_before_crossing(self):
        goal=dict(room=[0,0,224],x=27,y=48,tolerance=3,skill='shielded_axis')
        planner=ProgressionPlanner(WorldMemory(),[goal])
        self.assertEqual(planner.action({},replace(STATE,room=(0,0,225),x=12,y=60),Policy()),[1,2])
        self.assertEqual(planner.action({},replace(STATE,room=(0,0,225),x=12,y=48),Policy()),[3,2])
        self.assertEqual(planner.last_decision['kind'],'scripted_shielded_axis')

    def test_shielded_crossing_requires_equipped_shield_and_adjacent_room(self):
        goal=dict(room=[0,0,224],x=27,y=48,skill='shielded_axis')
        planner=ProgressionPlanner(WorldMemory(),[goal])
        self.assertIsNone(planner.action({},replace(STATE,b_item=0),Policy()))
        self.assertEqual(planner.status,'shield_not_equipped')
        planner=ProgressionPlanner(WorldMemory(),[goal])
        self.assertIsNone(planner.action({},STATE,Policy()))
        self.assertEqual(planner.status,'missing_adjacent_route')

    def test_narrow_crossing_target_does_not_finish_eight_pixels_early(self):
        goal=dict(room=[0,0,224],x=27,y=48,tolerance=3,skill='shielded_axis')
        planner=ProgressionPlanner(WorldMemory(),[goal])
        self.assertEqual(planner.action({},replace(STATE,room=(0,0,224),x=35,y=48),Policy()),[3,2])
        self.assertIsNone(planner.action({},replace(STATE,room=(0,0,224),x=28,y=48),Policy()))
        self.assertEqual(planner.status,'guidance_prefix_complete')

    def test_memory_supplies_intermediate_observed_room(self):
        path=ROOT/'runs/world-memory-v1/generation-1.json'
        if not path.exists():self.skipTest('Verified memory required')
        memory=WorldMemory.load(path)
        p=ProgressionPlanner(memory,[dict(room=[0,0,242],x=80,y=80)])
        policy=Policy();p.action({},replace(STATE,room=(1,16,163),x=110,y=70),policy)
        self.assertEqual(p.last_decision['kind'],'memory_navigation')
        self.assertEqual(policy.goal['room'],[0,0,162])
        self.assertIn(p.last_decision['memory_evidence'],memory.observations)


if __name__=='__main__':unittest.main()
