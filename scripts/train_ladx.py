"""Bounded PPO training with immutable shards and verified boundary resume."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import time
import uuid

import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.training_env import TrainingEnv
from gameboy_agent.ladx_baseline import CustomFeatureExtractor
from gameboy_agent.checkpoint import save_checkpoint, restore_checkpoint, digest


class Recorder(BaseCallback):
    def __init__(self,state,run):
        super().__init__()
        self.state=state
        self.run=run
        self.rows=[]

    def _on_step(self):
        info=self.locals['infos'][0]
        done=bool(self.locals['dones'][0])
        obs=info.get('terminal_observation') if done else {k:v[0] for k,v in self.locals['new_obs'].items()}
        h=hashlib.sha256()
        for k in sorted(obs):h.update(obs[k].tobytes())
        self.rows.append({'schema_version':'training-diagnostic-v1',
                          'run_id':self.state['run_id'],'producer_id':self.state['producer_id'],
                          'episode_id':self.state['episode_id'],
                          'index':self.state['trajectory_next_index'],
                          'action':self.locals['actions'][0].tolist(),
                          'observation_sha256':h.hexdigest(),
                          'reward':float(self.locals['rewards'][0]),
                          'reward_components':info['reward'],
                          'sword_acquired':info.get('sword_acquired',False),
                          'task_success':info.get('task_success',False),
                          'curriculum_kind':self.state['curriculum']['kind'],
                          'done':done,'truncated':bool(info.get('TimeLimit.truncated',False)),
                          'frames_advanced':info['frames_advanced'],'wait_frames':info['wait_frames'],
                          'phase':info['phase'], 'completion_evaluated':False,
                          'harness_privilege':'D','supervision':'autonomous_assisted_harness'})
        self.state['trajectory_next_index']+=1
        self.state['emulator_frames']+=info['frames_advanced']
        self.state['transition_wait_frames']+=info['wait_frames']
        room=list(info['phase']['room'])
        if room not in self.state['rooms_seen']:self.state['rooms_seen'].append(room)
        self.state['episode_reward']+=float(self.locals['rewards'][0])
        self.state['episode_steps']+=1
        if done:
            self.state['episodes_completed']+=1
            if info.get('death',False):self.state['deaths']+=1
            self.state['sword_successes']=self.state.get('sword_successes',0)+int(info.get('sword_acquired',False))
            self.state['recent_episodes'].append({'steps':self.state['episode_steps'],'reward':self.state['episode_reward']})
            self.state['recent_episodes']=self.state['recent_episodes'][-20:]
            self.state['episode_id']=str(uuid.uuid4())
            self.state['episode_reward']=0.0
            self.state['episode_steps']=0
        return True

    def flush(self):
        if not self.rows:return
        path=self.run/'shards'/f'{self.rows[0]["index"]:09}-{uuid.uuid4()}.jsonl'
        path.parent.mkdir(exist_ok=True)
        with path.open('x') as f:
            for row in self.rows:f.write(json.dumps(row)+'\n')
            f.flush();os.fsync(f.fileno())
        self.state['shards'].append({'path':str(path.resolve()),'sha256':digest(path),
                                     'first_index':self.rows[0]['index'],'rows':len(self.rows)})
        self.rows=[]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--steps',type=int,help='Total planned training horizon; defaults to 32768 for new runs')
    p.add_argument('--stop-after',type=int,help='Stop at this absolute step, retaining the full horizon')
    p.add_argument('--resume',type=Path)
    p.add_argument('--initial-state',type=Path)
    p.add_argument('--sword-curriculum',action='store_true')
    p.add_argument('--warm-start',type=Path,help='Transfer policy weights only; new optimizer and horizon')
    p.add_argument('--seed',type=int,default=0)
    p.add_argument('--entropy',type=float,default=0.01)
    p.add_argument('--checkpoint-every',type=int,default=2048)
    args=p.parse_args()
    if args.resume and (args.initial_state or args.sword_curriculum or args.warm_start):
        p.error('Resume retains the saved initial state and curriculum')
    if args.steps is not None and (args.steps<128 or args.steps%128):
        p.error('--steps must be a multiple of 128')
    if args.checkpoint_every < 128 or args.checkpoint_every % 128:
        p.error('--checkpoint-every must be a positive multiple of 128')
    if not np.isfinite(args.entropy) or args.entropy < 0:
        p.error('--entropy must be finite and nonnegative')
    run_id=str(uuid.uuid4());run=ROOT/'runs'/run_id;run.mkdir(parents=True)
    roms=list(ROOT.glob('*.gbc'))
    if len(roms)!=1:p.error('Exactly one root GBC ROM required')
    shutil.copy2(roms[0],run/'game.gbc')
    torch.set_num_threads(4)
    env=None
    try:
        if args.resume:
            model,env,state=restore_checkpoint(args.resume,run/'game.gbc')
            if args.steps is not None and args.steps!=state['target_timesteps']:
                p.error('Resume retains the saved training horizon; omit --steps or use the saved value')
            for shard in state['shards']:
                if digest(shard['path'])!=shard['sha256']:raise ValueError('Parent trajectory shard mismatch')
            state['parent_checkpoint']=str(args.resume.resolve())
            state['run_id']=run_id
            state['producer_id']=socket.gethostname()
        else:
            shutil.copy2(args.initial_state or ROOT/'references/LADXExperiments/ladx.gbc.state',run/'initial.state')
            env=TrainingEnv(run/'game.gbc',run/'initial.state',max_steps=2048,sword_curriculum=args.sword_curriculum)
            model=PPO('MultiInputPolicy',DummyVecEnv([lambda:env]),seed=args.seed,device='cpu',
                      n_steps=128,batch_size=64,n_epochs=2,learning_rate=0.00003,
                      gamma=0.996,vf_coef=0.5,ent_coef=args.entropy,
                      policy_kwargs={'features_extractor_class':CustomFeatureExtractor,
                                     'net_arch':[1024,1024],'activation_fn':torch.nn.ReLU},verbose=0)
            if args.warm_start:
                teacher=PPO.load(args.warm_start,device='cpu')
                model.policy.load_state_dict(teacher.policy.state_dict(),strict=True)
                del teacher
            state={'schema_version':'resumable-training-v1','run_id':run_id,
                   'producer_id':socket.gethostname(),'parent_checkpoint':None,
                   'target_timesteps':args.steps or 32768,'seed':args.seed,
                   'entropy_coefficient':args.entropy,
                   'weight_transfer':({'path':str(args.warm_start.resolve()),'sha256':digest(args.warm_start),
                                       'optimizer':'fresh','supervision':'demonstration_assisted_lineage'} if args.warm_start else None),
                   'trajectory_next_index':0,'shards':[],'episode_id':str(uuid.uuid4()),
                   'episode_reward':0.0,'episode_steps':0,'episodes_completed':0,'deaths':0,
                   'recent_episodes':[],'emulator_frames':0,'transition_wait_frames':0,'rooms_seen':[],
                   'curriculum':{'kind':'sword_sparse_v1' if args.sword_curriculum else 'fixed_savestate',
                                 'source_path':str((args.initial_state or ROOT/'references/LADXExperiments/ladx.gbc.state').resolve()),
                                 'state_sha256':digest(run/'initial.state')},
                   'planner':None,'harness_privilege':'D','completion_evaluated':False}
        target=state['target_timesteps']
        stop=args.stop_after or target
        if stop>target or stop<=model.num_timesteps or stop%model.n_steps:
            p.error('Stop must be a later rollout boundary within the saved training horizon')
        recorder=Recorder(state,run)
        # Configure SB3 once with the full horizon. Continue updates manually so
        # checkpoints occur after train(), not inside an incomplete rollout.
        _,callback=model._setup_learn(target-model.num_timesteps,recorder,False,'PPO',False)
        callback.on_training_start({}, {})
        started=time.monotonic()
        print(f'RUN {run}',flush=True)
        while model.num_timesteps<stop:
            model.collect_rollouts(model.env,callback,model.rollout_buffer,n_rollout_steps=model.n_steps)
            model._update_current_progress_remaining(model.num_timesteps,target)
            model.train()
            if not all(torch.isfinite(v).all() for v in model.policy.parameters()):
                raise ValueError('Non-finite model parameter')
            recorder.flush()
            if model.num_timesteps%args.checkpoint_every==0 or model.num_timesteps==stop:
                state['elapsed_this_run_seconds']=time.monotonic()-started
                checkpoint=run/'checkpoints'/f'{model.num_timesteps:09}'
                save_checkpoint(checkpoint,model,env,experiment_state=state)
                state['latest_checkpoint']=str(checkpoint)
                (run/'progress.json').write_text(json.dumps(state,indent=2)+'\n')
                print(json.dumps({'step':model.num_timesteps,'episodes':state['episodes_completed'],
                                  'rooms':len(state['rooms_seen']),'deaths':state['deaths'],
                                  'seconds':round(time.monotonic()-started,1),
                                  'checkpoint':str(checkpoint)}),flush=True)
        callback.on_training_end()
        env.pyboy.screen.image.save(run/'screen.png')
        state['status']='completed' if stop==target else 'paused_at_checkpoint'
        (run/'result.json').write_text(json.dumps(state,indent=2)+'\n')
    except BaseException as exc:
        (run/'failure.json').write_text(json.dumps({'error':repr(exc)},indent=2)+'\n')
        raise
    finally:
        if env is not None:env.close()


if __name__=='__main__':main()
