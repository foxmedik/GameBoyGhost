"""Route advancement respects ordering, death, and per-goal budgets."""
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from gameboy_agent.skills import Senses
from route_progress import advance


class RouteProgressTest(unittest.TestCase):
    def state(self,x=20,health=8):return Senses((0,0,226),x,20,False,True,health,1,4)
    def test_goal_reached_on_last_action_advances_and_resets_budget(self):
        goals=[dict(room=[0,0,226],x=20,y=20),dict(room=[0,0,226],x=80,y=20)]
        p=dict(cursor=0,leg_steps=256,leg_start=100,completed=[])
        self.assertEqual(advance(self.state(),goals,p,356,256),'running')
        self.assertEqual(p['cursor'],1);self.assertEqual(p['leg_steps'],0);self.assertEqual(p['completed'][0]['actions'],256)
        self.assertEqual(advance(self.state(x=80),goals,p,370,256),'success')
    def test_later_goal_does_not_skip_current_goal(self):
        goals=[dict(room=[0,0,226],x=20,y=20),dict(room=[0,0,226],x=80,y=20)]
        p=dict(cursor=0,leg_steps=256,leg_start=0,completed=[])
        self.assertEqual(advance(self.state(x=80),goals,p,256,256),'navigation_timeout')
        self.assertEqual(p['cursor'],0)
    def test_death_precedes_goal_completion(self):
        p=dict(cursor=0,leg_steps=1,leg_start=0,completed=[])
        self.assertEqual(advance(self.state(health=0),[dict(room=[0,0,226],x=20,y=20)],p,1,256),'death')
        self.assertEqual(p['completed'],[])

if __name__=='__main__':unittest.main()
