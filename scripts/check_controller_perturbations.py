"""No-learning evaluation from explicitly recorded physical setup perturbations."""
import sys
from pathlib import Path
import numpy as np
import torch
from stable_baselines3 import PPO
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import environment,write
from control_context import ControlContext

def check(policy,out):
    model=PPO.load(policy,device='cpu');env=ControlContext(environment(out/'emulator','approach'))
    setups=[[],[[3,0]],[[3,0]]*2,[[3,0]]*3,[[1,0]],[[3,0],[1,0]],[[4,0]],[[2,0]]]
    rows=[]
    try:
        for i,setup in enumerate(setups):
            obs,_=env.reset(seed=20000+i)
            for action in setup:obs,_,_,_,_=env.step(np.asarray(action))
            actions=[]
            for step in range(512):
                action,_=model.predict(obs,deterministic=True);actions.append(action.tolist())
                obs,_,done,truncated,info=env.step(action)
                if done or truncated:break
            rows.append({'setup_actions':setup,'seen_setup_during_training':i<4,
                         'success':info['sword_acquired'],'death':info['death'],'steps':step+1,'actions':actions})
        write(out/'perturbation-evaluation.json',{'policy':str(policy),'learning_enabled':False,'harness_privilege':'D',
                'completion_evaluated':False,'episodes':rows})
        print([(r['seen_setup_during_training'],r['success'],r['steps']) for r in rows])
    finally:env.close()
if __name__=='__main__':
    torch.set_num_threads(2);check(Path(sys.argv[1]),Path(sys.argv[2]))
