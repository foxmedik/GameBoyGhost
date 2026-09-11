"""Frozen learned-tree evaluation on additional physical start perturbations."""
from pathlib import Path
import sys
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import environment,write
from control_context import ControlContext
from tree_controller import predict,features
from gameboy_agent.checkpoint import digest
policy=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False);tree=json.loads(policy.read_text())
cases=[]
for start in ('house','beach','approach'):
    setups=[[],[[0,0]],[[0,0]]*3,[[0,0]]*7,[[1,0]],[[2,0]],[[3,0]],[[4,0]]]
    if start=='house':setups += [[[3,0]]*3,[[4,0]]*2,[[1,0],[3,0]],[[2,0],[4,0]]]
    if '--heldout' in sys.argv:
        setups=[[[0,0]]*2,[[0,0]]*5,[[0,0]]*11,[[3,0],[2,0]],[[4,0],[2,0]],[[1,0],[4,0]]]
    if '--validation-v2' in sys.argv:
        setups=[[[0,0]]*4,[[0,0]]*8,[[0,0]]*15,[[3,0],[0,0],[0,0]]]
    if '--validation-v3' in sys.argv:
        setups=[[[0,0]]*6,[[0,0]]*9,[[0,0]]*12,[[3,0]]+[[0,0]]*4]
    cases += [(start,setup) for setup in setups]
rows=[]
for i,(start,setup) in enumerate(cases):
    env=ControlContext(environment(out/f'case-{i}',start));trace=[];success=False;error=None
    try:
        obs,_=env.reset(seed=30000+i)
        for action in setup:obs,_,_,_,_=env.step(np.asarray(action))
        assert env.unwrapped.pyboy.memory[0xDB4E]==0
        for step in range(1600):
            action=predict(tree,features(obs));trace.append(action.tolist())
            obs,_,done,truncated,info=env.step(action);success=info['sword_acquired']
            if done or truncated:break
        env.unwrapped.pyboy.screen.image.save(out/f'case-{i}-final.png')
    except Exception as exc:error=repr(exc)
    finally:env.close()
    write(out/f'case-{i}-actions.json',trace)
    rows.append({'case':i,'start':start,'setup_actions':setup,'success':success,'steps':len(trace),'error':error})
    write(out/'evaluation.json',{'policy':str(policy),'policy_sha256':digest(policy),'learning_enabled':False,
          'teacher_active':False,'split':'new_validation_v3' if '--validation-v3' in sys.argv else 'new_validation_v2' if '--validation-v2' in sys.argv else 'additional_untrained_setups' if '--heldout' in sys.argv else 'development_stress_setups','harness_privilege':'D','completion_evaluated':False,'episodes':rows})
    print(rows[-1],flush=True)
