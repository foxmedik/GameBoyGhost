"""Correct a learned tree on physical perturbations; keep all lineage/data."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import environment,write
from control_context import ControlContext
from route_teacher import RouteTeacher
from refine_sword_context import expert as close_expert
from tree_controller import fit_tree,predict,features,evaluate
from gameboy_agent.checkpoint import digest
source=Path(sys.argv[1]);policy=Path(sys.argv[2]);evaluation=Path(sys.argv[3]);out=Path(sys.argv[4]);out.mkdir(parents=True,exist_ok=False)
d=np.load(source);arrays={k:d[k].copy() for k in d.files};tree=json.loads(policy.read_text());obs_rows=[];labels=[];records=[]
cases=json.loads(evaluation.read_text())['episodes']
for i,case in enumerate(cases):
    if case['success']:continue
    for mixing in (1.0,.75):
        env=ControlContext(environment(out/f'capture-{i}-{mixing}',case['start']));teacher=RouteTeacher();rng=np.random.default_rng(i);success=False;error=None
        first_row=len(labels)
        try:
            obs,_=env.reset(seed=40000+i)
            for action in case['setup_actions']:obs,_,_,_,_=env.step(np.asarray(action))
            for step in range(1600):
                label=close_expert(env.unwrapped) if case['start']=='approach' else teacher.action(env)
                obs_rows.append(deepcopy(obs));labels.append(label)
                action=np.asarray(label) if rng.random()<mixing else predict(tree,features(obs))
                obs,_,done,truncated,info=env.step(action);success=info['sword_acquired']
                if done or truncated:break
        except Exception as exc:error=repr(exc)
        finally:env.close()
        if not success:
            del obs_rows[first_row:];del labels[first_row:]
        records.append({'accepted_for_training':success,'start':case['start'],'setup_actions':case['setup_actions'],'teacher_fraction':mixing,'success':success,'error':error})
        print(records[-1],flush=True)
additions={k:np.stack([o[k] for o in obs_rows]) for k in obs_rows[0]};additions.update(actions=np.asarray(labels),frames=np.arange(len(labels))*10)
arrays={k:np.concatenate((arrays[k],additions[k])) for k in arrays};np.savez_compressed(out/'demonstrations.npz',**arrays)
write(out/'demonstrations.json',{'supervision':'DAgger_tree_feedback_teacher','parent_data':str(source),'parent_sha256':digest(source),
      'parent_policy':str(policy),'parent_policy_sha256':digest(policy),'collection':records,'new_rows':len(labels)})
x=features(arrays)
if '--geometry' in sys.argv:x=x[:,:9]
new_tree=fit_tree(x,arrays['actions'][:,0]*4+arrays['actions'][:,1]);write(out/'policy.json',new_tree);evaluate(new_tree,out)
