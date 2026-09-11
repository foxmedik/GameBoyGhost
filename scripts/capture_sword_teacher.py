"""Feedback-scripted close-start demonstrations using the deployed action clock."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import environment,write
from gameboy_agent.checkpoint import digest

def capture(out,context=False):
    out.mkdir(parents=True,exist_ok=False)
    observations=[];actions=[];episodes=[]
    env=environment(out/'emulator','approach')
    if context:
        from control_context import ControlContext
        env=ControlContext(env)
    try:
        for seed in range(12):
            obs,_=env.reset(seed=seed)
            # Physical perturbations, disclosed as part of demonstration setup.
            for _ in range(seed%4):obs,_,_,_,_=env.step(np.array([3,0]))
            start=len(actions)
            for step in range(256):
                x=env.pyboy.memory[0xFF98];y=env.pyboy.memory[0xFF99]
                dialog=env.pyboy.memory[0xC19F]
                if dialog:action=[0,1 if step%2==0 else 0]
                elif x<84:action=[4,0]
                elif x>92:action=[3,0]
                elif y<83:action=[2,0]
                else:action=[0,1 if step%2==0 else 0]
                observations.append(deepcopy(obs));actions.append(action)
                obs,_,done,truncated,info=env.step(np.array(action))
                if done or truncated:break
            episodes.append({'seed':seed,'first_row':start,'rows':len(actions)-start,'success':info['sword_acquired']})
        arrays={k:np.stack([o[k] for o in observations]) for k in observations[0]}
        arrays.update(actions=np.asarray(actions),frames=np.arange(len(actions))*10)
        np.savez_compressed(out/'demonstrations.npz',**arrays)
        write(out/'demonstrations.json',{'supervision':'feedback_scripted_teacher','action_clock':'ten_ready_frames','control_context':context,
              'harness_privilege':'D','ram_edits_by_teacher':False,'policy_uses_teacher_at_evaluation':False,
              'episodes':episodes,'data_sha256':digest(out/'demonstrations.npz')})
        print(json.dumps(episodes))
    finally:env.close()
if __name__=='__main__':capture(Path(sys.argv[1]),context="--context" in sys.argv)
