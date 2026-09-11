"""Bounded map-assisted navigation prefix with memory-backed intermediate goals.

This first integration approaches the forest; it does not encode the full quest.
"""
from collections import Counter
from copy import deepcopy

from gameboy_agent.navigation import reached


class ProgressionPlanner:
    def __init__(self, memory, goals, *, goal_budget=256, recovery_limit=2):
        self.memory=memory
        self.goals=deepcopy(goals)
        self.goal_budget=goal_budget
        self.recovery_limit=recovery_limit
        self.cursor=0
        self.leg_steps=0
        self.recoveries=0
        self.positions=[]
        self.events=[]
        self.pending_recovery=[]
        self.last_decision=None
        self.status='running'

    def state(self):
        return deepcopy({k:v for k,v in vars(self).items() if k!='memory'})

    def restore(self, state):
        if state['goals']!=self.goals or state['goal_budget']!=self.goal_budget:
            raise ValueError('Planner checkpoint contract mismatch')
        for key,value in deepcopy(state).items():
            if key=='memory' or key not in vars(self):raise ValueError('Unexpected planner field')
            setattr(self,key,value)

    def action(self, obs, senses, policy):
        if senses.health==0:
            self.status='death';return None
        if senses.dialogue:
            self.leg_steps+=1
            if self.leg_steps>self.goal_budget:
                self.status='dialogue_timeout';return None
            self.last_decision={'kind':'physical_dialogue_advance'}
            return [0,self.leg_steps%2]
        while self.cursor<len(self.goals) and reached(senses.room,senses.x,senses.y,self.goals[self.cursor],tolerance=self.goals[self.cursor].get('tolerance',8)):
            self.events.append(dict(kind='guidance_goal_reached',index=self.cursor,steps=self.leg_steps))
            self.cursor+=1;self.leg_steps=0;self.recoveries=0;self.positions=[];self.pending_recovery=[]
        if self.cursor==len(self.goals):
            self.status='guidance_prefix_complete';return None
        if self.leg_steps>=self.goal_budget:
            self.status='navigation_timeout';return None
        goal=self.goals[self.cursor]
        query=self.memory.route(list(senses.room),goal['room'])
        target={k:goal[k] for k in ('room','x','y')}
        evidence=None
        if query['status']=='observed_route' and len(query['legs'])>1:
            edge=self.memory.observations[query['legs'][0]['observation']]
            arrival=edge['details']['settled_arrival']
            target=dict(room=arrival['room'],x=arrival['position'][0],y=arrival['position'][1])
            evidence=query['legs'][0]['observation']
        self.positions.append([*senses.room,senses.x//8,senses.y//8])
        self.positions=self.positions[-64:]
        loop=len(self.positions)==64 and len({tuple(p) for p in self.positions})<=4
        if loop and not self.pending_recovery:
            if self.recoveries>=self.recovery_limit:
                self.status='repeated_local_stall';return None
            # A short orthogonal physical probe, selected from observed local
            # attempts, is labeled as recovery rather than learned navigation.
            scores=[]
            for direction,name,dx,dy in ((1,'up',0,-1),(2,'down',0,1),(3,'left',-1,0),(4,'right',1,0)):
                history=self.memory.movement_evidence(list(senses.room),[senses.x//8,senses.y//8],name)
                visits=sum(p[-2:]==[senses.x//8+dx,senses.y//8+dy] for p in self.positions)
                scores.append((len(history['outcomes']['no_displacement'])+visits,direction))
            direction=sorted(scores)[self.recoveries%4][1]
            self.pending_recovery=[[direction,0]]*3
            self.recoveries+=1;self.positions=[]
            self.events.append(dict(kind='physical_recovery_probe',goal=self.cursor,direction=direction))
        self.leg_steps+=1
        self.last_decision=dict(kind='memory_navigation' if evidence else 'provided_map_navigation',
            guidance_index=self.cursor,target=target,route_status=query['status'],
            memory_evidence=evidence,conditions_checked=False)
        if self.pending_recovery:
            self.last_decision['kind']='physical_recovery_probe'
            return self.pending_recovery.pop(0)
        if goal.get('skill')=='shielded_axis':
            shield=1 if senses.a_item==4 else 2 if senses.b_item==4 else 0
            if not shield:
                self.status='shield_not_equipped';return None
            source=list(senses.room);destination=target['room']
            if source[:2]!=destination[:2]:
                self.status='unsupported_shielded_transition';return None
            dx=target['x']-senses.x;dy=target['y']-senses.y
            if source!=destination:
                room_dx=destination[2]%16-source[2]%16
                room_dy=destination[2]//16-source[2]//16
                if abs(room_dx)+abs(room_dy)!=1:
                    self.status='missing_adjacent_route';return None
                # Align the crossing lane before crossing a room boundary.
                if room_dx:
                    movement=(2 if dy>0 else 1) if abs(dy)>2 else (4 if room_dx>0 else 3)
                else:
                    movement=(4 if dx>0 else 3) if abs(dx)>2 else (2 if room_dy>0 else 1)
            else:
                movement=(4 if dx>0 else 3) if abs(dx)>2 else (2 if dy>0 else 1)
            self.last_decision['kind']='scripted_shielded_axis'
            return [movement,shield]
        return policy.action(obs,senses.room,target)
