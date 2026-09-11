"""Recollect a consistent teacher across the complete development suite."""
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
from tree_controller import fit_tree,features,evaluate
from gameboy_agent.checkpoint import digest
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
files=[Path('runs/tree-route-stress-v2/evaluation.json'),Path('runs/tree-route-frozen-eval-v1/evaluation.json'),Path('runs/tree-consistent-validation-v1/evaluation.json')]
cases=[c for p in files for c in json.loads(p.read_text())['episodes']];observations=[];labels=[];records=[]
for i,case in enumerate(cases):
    env=ControlContext(environment(out/f'capture-{i}',case['start']));teacher=RouteTeacher();begin=len(labels);success=False;error=None
    try:
        obs,_=env.reset(seed=50000+i)
        for action in case['setup_actions']:obs,_,_,_,_=env.step(np.asarray(action))
        for step in range(1600):
            action=close_expert(env.unwrapped) if case['start']=='approach' else teacher.action(env)
            observations.append(deepcopy(obs));labels.append(action)
            obs,_,done,truncated,info=env.step(np.asarray(action));success=info['sword_acquired']
            if done or truncated:break
    except Exception as exc:error=repr(exc)
    finally:env.close()
    if not success:del observations[begin:];del labels[begin:]
    records.append({'case':i,'start':case['start'],'setup_actions':case['setup_actions'],'success':success,'error':error})
    print(records[-1],flush=True)
arrays={k:np.stack([o[k] for o in observations]) for k in observations[0]};arrays.update(actions=np.asarray(labels),frames=np.arange(len(labels))*10)
np.savez_compressed(out/'demonstrations.npz',**arrays)
write(out/'demonstrations.json',{'supervision':'consistent_feedback_route_teacher','teacher_sha256':digest(ROOT/'scripts/route_teacher.py'),
      'cases':records,'rows':len(labels),'only_successful_episodes':True,'harness_privilege':'D'})
x=features(arrays)[:,:8].copy();x[:,3]=0
tree=fit_tree(x,arrays['actions'][:,0]*4+arrays['actions'][:,1]);write(out/'policy.json',tree);evaluate(tree,out)
