"""Autonomous bounded correction loop, with all trials and failures retained."""
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
from route_teacher import RouteTeacher
from refine_sword_context import expert as close_expert
from gameboy_agent.checkpoint import digest


def evaluate(policy,out,extra=False):
    model=PPO.load(policy,device='cpu');records=[]
    cases=[('house',[]),('house',[[3,0]]),('house',[[3,0]]*2),('beach',[]),('approach',[])]
    if extra:cases=[('house',[[4,0]]),('house',[[1,0]]),('house',[[3,0]]*3),('house',[[2,0]]),('beach',[[1,0]]),('approach',[[1,0]])]
    for i,(start,setup) in enumerate(cases):
        env=ControlContext(environment(out/f'eval-{i}',start));trace=[];error=None;success=False;death=False
        try:
            obs,_=env.reset(seed=20000+i)
            for action in setup:obs,_,_,_,_=env.step(np.asarray(action))
            for step in range(1600):
                action,_=model.predict(obs,deterministic=True);m=env.unwrapped.pyboy.memory
                trace.append({'action':action.tolist(),'x':int(m[0xFF98]),'y':int(m[0xFF99]),
                              'room':[int(m[a]) for a in (0xDBA5,0xFFF7,0xFFF6)],'dialog':int(m[0xC19F])})
                obs,_,done,truncated,info=env.step(action);success=info['sword_acquired'];death=info['death']
                if done or truncated:break
            env.unwrapped.pyboy.screen.image.save(out/f'eval-{i}-final.png')
        except Exception as exc:error=repr(exc)
        finally:env.close()
        write(out/f'eval-{i}-trace.json',trace)
        records.append({'start':start,'setup_actions':setup,'success':success,'death':death,'steps':len(trace),'error':error})
    write(out/'evaluation.json',{'policy':str(policy),'teacher_active':False,'deterministic':True,'additional_setups':extra,'episodes':records})
    return records


def main():
    root=Path(sys.argv[1]);policy=Path(sys.argv[2]);root.mkdir(parents=True,exist_ok=False)
    data=np.load(policy.parent/'demonstrations.npz');arrays={k:data[k].copy() for k in data.files}
    rounds=[];torch.set_num_threads(4)
    initial=root/'initial';initial.mkdir()
    if len(sys.argv)>3:
        previous=Path(sys.argv[3]);results=json.loads(previous.read_text())['episodes']
        write(initial/'reused-evaluation.json',{'source':str(previous),'sha256':digest(previous)})
    else:results=evaluate(policy,initial)
    print('INITIAL',results,flush=True)
    for number in range(4):
        out=root/f'round-{number}';out.mkdir();model=PPO.load(policy,device='cpu')
        observations=[];labels=[];collection=[];rng=np.random.default_rng(300+number)
        for episode,start in enumerate(['house']*4+['beach']*2+['approach']*2):
            env=ControlContext(environment(out/f'capture-{episode}',start));teacher=RouteTeacher();error=None;success=False
            try:
                obs,_=env.reset(seed=episode)
                if start=='house':
                    for _ in range(episode%3):obs,_,_,_,_=env.step(np.asarray([3,0]))
                for step in range(1600):
                    label=close_expert(env.unwrapped) if start=='approach' else teacher.action(env)
                    observations.append(deepcopy(obs));labels.append(label)
                    learned,_=model.predict(obs,deterministic=True)
                    action=np.asarray(label) if rng.random()<.75 else learned
                    obs,_,done,truncated,info=env.step(action);success=info['sword_acquired']
                    if done or truncated:break
            except Exception as exc:error=repr(exc)
            finally:env.close()
            collection.append({'start':start,'success':success,'error':error})
        additions={k:np.stack([o[k] for o in observations]) for k in observations[0]}
        additions.update(actions=np.asarray(labels),frames=np.arange(len(labels))*10)
        arrays={k:np.concatenate((arrays[k],additions[k])) for k in arrays}
        np.savez_compressed(out/'demonstrations.npz',**arrays)
        write(out/'demonstrations.json',{'supervision':'DAgger_full_route_feedback_teacher','teacher_action_fraction':.75,
              'collection':collection,'new_rows':len(labels),'parent_policy':str(policy),'parent_sha256':digest(policy),
              'preserved_close_demonstrations':True,'harness_privilege':'D','ram_edits_by_teacher':False})
        clone(out,50,initial_policy=policy);policy=out/'imitation-policy.zip';results=evaluate(policy,out)
        record={'round':number,'policy':str(policy),'successes':sum(r['success'] for r in results),'episodes':results}
        rounds.append(record);write(root/'progress.json',rounds);print('ROUND',json.dumps(record),flush=True)
        if all(r['success'] for r in results):
            extra=out/'additional-setups';extra.mkdir();evaluate(policy,extra,extra=True);break
    write(root/'finished.json',{'status':'completed_bounded_experiment','rounds':len(rounds),'last_policy':str(policy),
                              'reliability_target_met_on_development_cases':all(r['success'] for r in results)})
if __name__=='__main__':main()
