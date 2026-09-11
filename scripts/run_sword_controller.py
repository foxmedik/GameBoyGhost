"""Run the learned tree without a teacher; checkpoint via verified episode replay."""
from copy import deepcopy
import argparse
import json
import importlib.metadata
from pathlib import Path
import pickle
import shutil
import socket
import sys
import uuid
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import environment,write
from control_context import ControlContext
from tree_controller import predict,features
from gameboy_agent.training_env import TrainingEnv
from gameboy_agent.checkpoint import fingerprint,digest


def sources():
    return list((ROOT/'src/gameboy_agent').glob('*.py'))+[ROOT/'scripts'/name for name in
               ['control_context.py','tree_controller.py','run_sword_controller.py']]


def save(directory,base,policy,progress):
    directory.mkdir(parents=True,exist_ok=False)
    with (directory/'environment.pkl').open('xb') as f:pickle.dump({k:deepcopy(v) for k,v in vars(base).items() if k!='pyboy'},f)
    with (directory/'emulator.state').open('xb') as f:base.pyboy.save_state(f)
    shutil.copy2(base.init_state,directory/'initial.state');write(directory/'policy.json',policy);write(directory/'progress.json',progress)
    write(directory/'manifest.json',{'schema':'deterministic-tree-checkpoint-v1','fingerprint':fingerprint(base),
          'rom_sha256':digest(base.config['gb_path']),
          'versions':{name:importlib.metadata.version(name) for name in ['pyboy','numpy','gymnasium']},'restore_method':'verified_episode_replay',
          'sources':{str(p.relative_to(ROOT)):digest(p) for p in sources()},
          'artifacts':{p.name:digest(p) for p in directory.iterdir()},'optimizer':None,'policy_rng':None})


def restore(checkpoint,out):
    manifest=json.loads((checkpoint/'manifest.json').read_text())
    for name,version in manifest['versions'].items():
        if importlib.metadata.version(name)!=version:raise ValueError('Checkpoint dependency mismatch')
    for name,sha in manifest['artifacts'].items():
        if digest(checkpoint/name)!=sha:raise ValueError('Checkpoint artifact mismatch')
    for name,sha in manifest['sources'].items():
        if digest(ROOT/name)!=sha:raise ValueError('Checkpoint source mismatch')
    rom=out/'game.gbc';shutil.copy2(next(ROOT.glob('*.gbc')),rom)
    if digest(rom)!=manifest['rom_sha256']:raise ValueError('ROM mismatch')
    with (checkpoint/'environment.pkl').open('rb') as f:attrs=pickle.load(f) # Trusted local artifact, after hashes.
    base=TrainingEnv(rom,checkpoint/'initial.state',max_steps=attrs['config']['max_steps'],sword_curriculum=True)
    try:
        base.reset(seed=attrs['episode_seed'])
        for action in attrs['episode_actions']:base.step(np.asarray(action))
        if fingerprint(base)!=manifest['fingerprint']:raise ValueError('Replay fingerprint mismatch')
        vars(base).update(attrs);base.config=deepcopy(base.config)
        base.config['gb_path']=str(rom.resolve());base.init_state=str((checkpoint/'initial.state').resolve())
        base.config['init_state']=base.init_state
        return base,json.loads((checkpoint/'policy.json').read_text()),json.loads((checkpoint/'progress.json').read_text())
    except BaseException:base.close();raise


def main():
    p=argparse.ArgumentParser();p.add_argument('--policy',type=Path);p.add_argument('--resume',type=Path)
    p.add_argument('--start',choices=['house','beach','approach'],default='house');p.add_argument('--stop-after',type=int)
    p.add_argument('--out',type=Path);args=p.parse_args()
    if not args.policy and not args.resume:
        config_path=ROOT/'configs/sword_controller.json'
        if not config_path.exists():p.error('No selected controller; provide --policy')
        config=json.loads(config_path.read_text());args.policy=ROOT/config['policy_path']
        if digest(args.policy)!=config['policy_sha256']:raise ValueError('Selected policy integrity mismatch')
    if args.policy and args.resume:p.error('Choose --policy or --resume')
    out=args.out or ROOT/'runs'/str(uuid.uuid4());out.mkdir(parents=True,exist_ok=False)
    if args.resume:
        base,policy,progress=restore(args.resume,out)
        progress['parent_run_id']=progress['run_id'];progress['run_id']=str(uuid.uuid4())
    else:
        base=environment(out,args.start);base.reset(seed=0);policy=json.loads(args.policy.read_text())
        progress={'run_id':str(uuid.uuid4()),'episode_id':str(uuid.uuid4()),'producer_id':socket.gethostname(),'harness_privilege':'D','supervision':'demonstration_assisted_tree',
                  'teacher_active':False,'completion_evaluated':False,'start':args.start,'actions':[]}
    progress['parent_checkpoint']=str(args.resume) if args.resume else None
    env=ControlContext(base);obs=env.observation(base.cached_observation);stop=args.stop_after or 1600
    try:
        if base.needs_reset:raise ValueError('Checkpoint episode already ended')
        if stop<=len(progress['actions']):raise ValueError('Stop must exceed saved step')
        with (out/'trajectory.jsonl').open('x') as log:
            while len(progress['actions'])<stop:
                action=predict(policy,features(obs));obs,reward,done,truncated,info=env.step(action)
                progress['actions'].append(action.tolist())
                log.write(json.dumps({'schema':'sword-controller-trajectory-v1','run_id':progress['run_id'],
                                      'episode_id':progress['episode_id'],'producer_id':progress['producer_id'],
                                      'harness_privilege':'D','supervision':'demonstration_assisted_tree',
                                      'teacher_active':False,'completion_evaluated':False,'index':len(progress['actions'])-1,'action':action.tolist(),'reward':reward,
                                      'sword_acquired':info['sword_acquired'],'phase':info['phase']})+'\n')
                if done or truncated:break
        progress.update(sword_acquired=bool(base.pyboy.memory[0xDB4E]>0),steps=len(progress['actions']),
                        status='ended' if base.needs_reset else 'paused',fingerprint=fingerprint(base))
        save(out/f'checkpoint-{len(progress["actions"]):06}',base,policy,progress)
        write(out/'result.json',progress);base.pyboy.screen.image.save(out/'final.png');print(out,progress['status'],progress['sword_acquired'],progress['steps'])
    finally:env.close()
if __name__=='__main__':main()
