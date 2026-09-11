"""Fixed learned sword skill followed by a supplied navigation goal."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import torch
from gameboy_agent.navigation import NavigationController,reached
from gameboy_agent.training_env import TrainingEnv
from gameboy_agent.dataset import sha256
from gameboy_agent.checkpoint import fingerprint
from control_context import ControlContext
from tree_controller import predict,features
from sword_imitation import STARTS
from run_skill_chain import senses


def source_hashes():
    paths=list((ROOT/'src/gameboy_agent').glob('*.py'))
    paths += [ROOT/'scripts'/name for name in ('run_navigation_chain.py','control_context.py','tree_controller.py','sword_imitation.py','run_skill_chain.py')]
    return {str(p.relative_to(ROOT)):sha256(p) for p in paths}


def run(out,checkpoint=None,*,start='house',goal=None,budget=384,stop_after=None,resume=None):
    torch.set_num_threads(1);out=Path(out).resolve();saved=None
    if resume:
        resume=Path(resume).resolve();manifest=json.loads((resume/'manifest.json').read_text())
        if manifest['sources']!=source_hashes():raise ValueError('Resume source mismatch')
        for name,h in manifest['artifacts'].items():
            if sha256(resume/name)!=h:raise ValueError('Resume artifact mismatch')
        saved=json.loads((resume/'result.json').read_text())
        if saved['status']!='paused':raise ValueError('Only a paused run can resume')
        goal,start,budget=saved['goal'],saved['start'],saved['budget']
        checkpoint=resume/'policy.pt';initial=resume/'initial.state';sword_path=resume/'sword.json'
        if stop_after is not None and stop_after<=len(saved['actions']):raise ValueError('Stop must exceed saved step')
    else:
        checkpoint=Path(checkpoint)
        metadata=json.loads(checkpoint.with_suffix('.json').read_text())
        if sha256(checkpoint)!=metadata['sha256']:raise ValueError('Policy mismatch')
        initial=STARTS[start];selection=json.loads((ROOT/'configs/sword_controller.json').read_text())
        sword_path=ROOT/selection['policy_path']
        if sha256(sword_path)!=selection['policy_sha256']:raise ValueError('Sword policy mismatch')
    if budget<1 or goal is None:raise ValueError('A goal and positive budget are required')
    rom=next(ROOT.glob('*.gbc'))
    if saved and sha256(rom)!=manifest['rom_sha256']:raise ValueError('ROM mismatch')
    out.mkdir(parents=True,exist_ok=False)
    for source,name in ((checkpoint,'policy.pt'),(initial,'initial.state'),(sword_path,'sword.json'),(rom,'game.gbc')):
        shutil.copy2(source,out/name)
    base=TrainingEnv(out/'game.gbc',out/'initial.state',max_steps=1600+budget+1,sword_curriculum=False)
    env=ControlContext(base);policy=NavigationController(out/'policy.pt');tree=json.loads((out/'sword.json').read_text())
    actions=[];nav_steps=0;sword_step=None;status='paused';damage=0;nav_damage=0
    try:
        obs,_=env.reset(seed=0)
        if saved:
            for action in saved['actions']:obs,_,_,_,_=env.step(np.asarray(action))
            if fingerprint(base)!=saved['fingerprint']:raise ValueError('Replay fingerprint mismatch')
            actions=list(saved['actions']);nav_steps=saved['navigation_steps'];sword_step=saved['sword_step']
            damage=saved['damage'];nav_damage=saved['navigation_damage']
        with (out/'trajectory.jsonl').open('x') as log:
            while stop_after is None or len(actions)<stop_after:
                state=senses(base)
                if state.health==0:status='death';break
                if state.sword:
                    if sword_step is None:sword_step=len(actions)
                    if reached(state.room,state.x,state.y,goal):status='success';break
                    if nav_steps>=budget:status='navigation_timeout';break
                    action=policy.action(obs,state.room,goal);skill='navigation';nav_steps+=1
                else:
                    if len(actions)>=1600:status='sword_timeout';break
                    action=predict(tree,features(obs)).tolist();skill='sword'
                obs,reward,done,truncated,_=env.step(np.asarray(action));after=senses(base)
                loss=max(0,state.health-after.health);damage+=loss
                if skill=='navigation':nav_damage+=loss
                actions.append(action)
                log.write(json.dumps(dict(step=len(actions)-1,skill=skill,action=action,room=list(after.room),
                    x=after.x,y=after.y,health=after.health,reward=reward,goal=goal))+'\n')
                if done or truncated:status='death' if after.health==0 else 'environment_end';break
        result=dict(run_id=str(uuid.uuid4()),episode_id=saved['episode_id'] if saved else str(uuid.uuid4()),
            parent_checkpoint=str(resume) if resume else None,start=start,goal=goal,budget=budget,
            status=status,actions=actions,steps=len(actions),sword_step=sword_step,sword_acquired=senses(base).sword,
            navigation_steps=nav_steps,damage=damage,navigation_damage=nav_damage,
            fingerprint=fingerprint(base),final_state=senses(base).__dict__,harness_privilege='D',completion_evaluated=False,
            goal_source='explicit externally supplied destination; no general planner active')
        (out/'result.json').write_text(json.dumps(result,indent=2))
        with (out/'emulator.state').open('xb') as f:base.pyboy.save_state(f)
        base.pyboy.screen.image.save(out/'final.png')
        (out/'manifest.json').write_text(json.dumps(dict(sources=source_hashes(),rom_sha256=sha256(rom),
            artifacts={p.name:sha256(p) for p in out.iterdir() if p.is_file() and p.name!='game.gbc'}),indent=2))
        print(json.dumps({k:result[k] for k in ('start','status','steps','sword_step','navigation_steps','navigation_damage')}),flush=True)
        return result
    finally:env.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--checkpoint',type=Path)
    p.add_argument('--start',choices=list(STARTS),default='house');p.add_argument('--goal',type=int,nargs=5,metavar=('INDOOR','MAP','ROOM','X','Y'))
    p.add_argument('--budget',type=int,default=384);p.add_argument('--stop-after',type=int);p.add_argument('--resume',type=Path)
    a=p.parse_args()
    if not a.resume and (not a.checkpoint or not a.goal):p.error('--checkpoint and --goal are required for a new run')
    goal=dict(room=a.goal[:3],x=a.goal[3],y=a.goal[4]) if a.goal else None
    run(a.out,a.checkpoint,start=a.start,goal=goal,budget=a.budget,stop_after=a.stop_after,resume=a.resume)
