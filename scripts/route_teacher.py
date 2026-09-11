"""Feedback route teacher built from a verified policy-driven sword episode."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import environment,write
from control_context import ControlContext
from refine_sword_context import expert as close_expert
from gameboy_agent.checkpoint import digest
TRACE=ROOT/'runs/imitation-experiment-v1/route-bc-house-replay-house-seed-10003-trace.json'

class RouteTeacher:
    def __init__(self):self.trace=json.loads(TRACE.read_text());self.index=0
    def action(self,env):
        m=env.unwrapped.pyboy.memory;room=[m[0xDBA5],m[0xFFF7],m[0xFFF6]];x=m[0xFF98];y=m[0xFF99]
        if room==[1,16,163]:
            if y<70:
                if x<106:return [4,0]
                if x>114:return [3,0]
            if y<112:return [2,0]
            if x<76:return [4,0]
            if x>84:return [3,0]
            return [2,0]
        if m[0xC19F]:return [0,0 if env.unwrapped.last_action[1]==1 else 1]
        if room==[0,0,193]:
            if x<72:return [4,2]
            if x>83:return [3,2]
            return [2,2]
        if room==[0,0,209]:
            if y<84:return [3 if x>72 else 2,2]
            return [3,2]
        if room==[0,0,225]:
            if y<60:return [4 if x<52 else 2,2]
            if y<90:
                if x<100:return [1 if y>68 else 4,2]
                return [2,2]
            return [3 if x>72 else 4 if x<64 else 2,2]
        if room==[0,0,241]:
            if y<32:return [4 if x<104 else 2,2]
            if y<52:return [4 if x<120 else 2,2]
            return [4,2]
        if room==[0,0,242]:
            if x>=60 and y>=75:return close_expert(env.unwrapped)
            if x<28 and y<60:return [4 if x<24 else 2,2]
            if x<40 and y<68:return [4,2]
            if x<60 and y<90:return [2,2]
            return [4,2]
        if m[0xC19F]:return [0,0 if env.unwrapped.last_action[1]==1 else 1]
        matches=[i for i,r in enumerate(self.trace[:600]) if r['room']==room and i>=self.index-8]
        if not matches:raise RuntimeError(f'Outside demonstrated route: {room} at {x},{y}')
        # Follow spatially matching progress, skipping repeated blocked actions.
        distance=lambda i:abs(self.trace[i]['x']-x)+abs(self.trace[i]['y']-y)
        nearest=min(distance(i) for i in matches)
        candidates=[i for i in matches if distance(i)<=nearest+1]
        index=max(candidates)
        self.index=max(self.index,index)
        return self.trace[index]['action']

def capture(out,episodes=1):
    out.mkdir(parents=True,exist_ok=False);env=ControlContext(environment(out/'emulator','house'))
    observations=[];actions=[];records=[]
    try:
        for episode in range(episodes):
            obs,_=env.reset(seed=episode);teacher=RouteTeacher();trace=[]
            for _ in range(episode%3):obs,_,_,_,_=env.step(np.asarray([3,0]))
            success=False;error=None
            try:
                for step in range(2048):
                    action=teacher.action(env);observations.append(deepcopy(obs));actions.append(action)
                    m=env.unwrapped.pyboy.memory
                    trace.append({'index':teacher.index,'x':int(m[0xFF98]),'y':int(m[0xFF99]),'room':[int(m[a]) for a in (0xDBA5,0xFFF7,0xFFF6)],'action':action})
                    obs,_,done,truncated,info=env.step(np.asarray(action));success=info['sword_acquired']
                    if done or truncated:break
            except Exception as exc:error=repr(exc)
            record={'episode':episode,'success':success,'steps':len(trace),'error':error}
            write(out/f'episode-{episode}.json',trace);records.append(record);print(record,flush=True)
        arrays={k:np.stack([o[k] for o in observations]) for k in observations[0]}
        arrays.update(actions=np.asarray(actions),frames=np.arange(len(actions))*10)
        np.savez_compressed(out/'demonstrations.npz',**arrays)
        write(out/'demonstrations.json',{'supervision':'feedback_route_teacher','source_trace_sha256':digest(TRACE),
              'episodes':records,'action_clock':'ten_ready_frames','ram_edits_by_teacher':False,'harness_privilege':'D'})
    finally:env.close()
if __name__=='__main__':capture(Path(sys.argv[1]),int(sys.argv[2]) if len(sys.argv)>2 else 1)
