"""Aggregate corrective teacher labels at states visited by the learned policy."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import numpy as np
import torch
from stable_baselines3 import PPO
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import environment,clone,write
from control_context import ControlContext
from gameboy_agent.checkpoint import digest

def expert(env):
    m=env.pyboy.memory;x=m[0xFF98];y=m[0xFF99]
    if m[0xC19F]:return [0,0 if env.last_action[1]==1 else 1]
    if x<84:return [4,0]
    if x>92:return [3,0]
    if y<83:return [2,0]
    return [0,0 if env.last_action[1]==1 else 1]

def main():
    root=Path(sys.argv[1]);initial=Path(sys.argv[2]);data=np.load(initial.parent/'demonstrations.npz')
    arrays={k:data[k].copy() for k in data.files};policy=initial
    records=[];torch.set_num_threads(4)
    for round_index in range(3):
        out=root/f'round-{round_index}';out.mkdir(parents=True,exist_ok=False)
        model=PPO.load(policy,device='cpu');env=ControlContext(environment(out/'capture','approach'))
        observations=[];labels=[];rng=np.random.default_rng(100+round_index)
        try:
            for episode in range(8):
                obs,_=env.reset(seed=episode)
                for _ in range(episode%4):obs,_,_,_,_=env.step(np.array([3,0]))
                for step in range(256):
                    teacher=expert(env);observations.append(deepcopy(obs));labels.append(teacher)
                    learned,_=model.predict(obs,deterministic=True)
                    action=np.asarray(teacher) if rng.random()<.5 else learned
                    obs,_,done,truncated,info=env.step(action)
                    if done or truncated:break
        finally:env.close()
        additions={k:np.stack([o[k] for o in observations]) for k in observations[0]}
        additions.update(actions=np.asarray(labels),frames=np.arange(len(labels))*10)
        arrays={k:np.concatenate((arrays[k],additions[k])) for k in arrays}
        np.savez_compressed(out/'demonstrations.npz',**arrays)
        write(out/'demonstrations.json',{'supervision':'DAgger_feedback_scripted_teacher',
              'teacher_action_fraction':.5,'new_rows':len(labels),'total_rows':len(arrays['actions']),
              'parent_policy':str(policy),'data_sha256':digest(out/'demonstrations.npz'),
              'harness_privilege':'D','ram_edits_by_teacher':False})
        clone(out,40,initial_policy=policy);policy=out/'imitation-policy.zip'
        model=PPO.load(policy,device='cpu');env=ControlContext(environment(out/'evaluation','approach'))
        successes=[]
        try:
            for offset in (0,1,2,3):
                obs,_=env.reset(seed=10000)
                for _ in range(offset):obs,_,_,_,_=env.step(np.array([3,0]))
                trace=[]
                for step in range(512):
                    action,_=model.predict(obs,deterministic=True)
                    obs,_,done,truncated,info=env.step(action)
                    trace.append(action.tolist())
                    if done or truncated:break
                successes.append({'left_setup_actions':offset,'success':info['sword_acquired'],'steps':step+1,'actions':trace})
        finally:env.close()
        write(out/'deterministic-evaluation.json',successes)
        records.append({'round':round_index,'policy':str(policy),'successes':sum(x['success'] for x in successes),'episodes':4})
        write(root/'results.json',records);print('DAGGER',json.dumps(records[-1]),flush=True)
        if all(x['success'] for x in successes):break
if __name__=='__main__':main()
