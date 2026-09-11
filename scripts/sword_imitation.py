"""Labeled demonstration/imitation experiment; never autonomous fixture claims."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random
import shutil
import sys
import time
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.training_env import TrainingEnv
from gameboy_agent.ladx_baseline import CustomFeatureExtractor
from gameboy_agent.checkpoint import digest,save_checkpoint
from gameboy_agent.transitions import world_ready,read_phase
STARTS={'approach':ROOT/'runs/sword-curriculum-v1/sword_approach.state',
        'beach':ROOT/'runs/sword-curriculum-v1/beach_route.state',
        'house':ROOT/'references/LADXExperiments/ladx.gbc.state'}
BUTTONS=('up','down','left','right','a','b','start','select')

def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')

def environment(out,start):
    out.mkdir(parents=True,exist_ok=True)
    rom=out/'game.gbc'
    if not rom.exists():shutil.copy2(next(ROOT.glob('*.gbc')),rom)
    return TrainingEnv(rom,STARTS[start],max_steps=2048,sword_curriculum=True)

def model_for(env):
    from control_context import ContextExtractor
    return PPO('MultiInputPolicy',DummyVecEnv([lambda:env]),seed=0,device='cpu',n_steps=128,batch_size=64,n_epochs=2,
               learning_rate=3e-5,gamma=.996,ent_coef=.01,
               policy_kwargs={'features_extractor_class':ContextExtractor if 'control' in env.observation_space.spaces else CustomFeatureExtractor,'net_arch':[1024,1024],'activation_fn':torch.nn.ReLU},verbose=0)

def evaluate(out,policy,tag,seeds=(10000,10001,10002,10003),steps=2048):
    results=[]
    for start in STARTS:
        env=environment(out/('eval-'+tag+'-'+start),start)
        if 'control' in policy.observation_space.spaces:
            from control_context import ControlContext
            env=ControlContext(env)
        try:
            for i,seed in enumerate(seeds):
                random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
                obs,_=env.reset(seed=seed);history=[];counts=Counter();success=False
                for step in range(steps):
                    action,_=policy.predict(obs,deterministic=i==0)
                    counts[tuple(action.tolist())]+=1
                    before={'x':int(env.pyboy.memory[0xFF98]),'y':int(env.pyboy.memory[0xFF99]),
                            'room':read_phase(env.pyboy)['room'],'dialog':int(env.pyboy.memory[0xC19F])}
                    obs,reward,done,truncated,info=env.step(action)
                    history.append({'step':step,'action':action.tolist(),**before,'reward':reward})
                    success=info['sword_acquired']
                    if done or truncated:break
                if success:env.pyboy.screen.image.save(out/f'{tag}-{start}-seed-{seed}-sword.png')
                results.append(dict(start=start,seed=seed,deterministic=i==0,steps=step+1,
                                    sword_acquired=success,death=info['death'],
                                    action_counts={str(k):v for k,v in counts.items()}))
                write(out/(f'{tag}-{start}-deterministic-trace.json' if i==0 else f'{tag}-{start}-seed-{seed}-trace.json'),history)
                if i==0:
                    env.pyboy.screen.image.save(out/f'{tag}-{start}-final.png')
        finally:env.close()
    write(out/f'evaluation-{tag}.json',{'supervision':tag,'harness_privilege':'D','completion_evaluated':False,'episodes':results})
    print('EVALUATION',tag,json.dumps(results),flush=True)
    return results

def capture(out):
    env=environment(out/'capture','house');obs,_=env.reset(seed=0)
    source=STARTS['house'];sequence=ROOT/'configs/fixtures/house_to_sword_and_push.json'
    with source.open('rb') as f:env.pyboy.load_state(f)
    observations=[];actions=[];frames=[];frame=0
    try:
        for segment in json.loads(sequence.read_text()):
            pressed=segment['buttons']
            action=[next((i for i,b in enumerate((None,'up','down','left','right')) if b in pressed),0),
                    1 if 'a' in pressed else 2 if 'b' in pressed else 0]
            for button in BUTTONS:
                (env.pyboy.button_press if button in pressed else env.pyboy.button_release)(button)
            for offset in range(segment['frames']):
                if world_ready(read_phase(env.pyboy)) and (frame%5==0 or offset==0):
                    observations.append(deepcopy(env.get_observation()));actions.append(action);frames.append(frame)
                    env.get_net_reward() # Refresh the same structured exploration memory.
                env.pyboy.tick(1,render=True);frame+=1
                if env.pyboy.memory[0xDB4E]>0:break
            if env.pyboy.memory[0xDB4E]>0:break
        assert env.pyboy.memory[0xDB4E]>0
        arrays={k:np.stack([o[k] for o in observations]) for k in observations[0]}
        arrays.update(actions=np.asarray(actions),frames=np.asarray(frames))
        np.savez_compressed(out/'demonstrations.npz',**arrays)
        write(out/'demonstrations.json',dict(schema='physical-fixture-supervision-v1',rows=len(actions),
              source_state_sha256=digest(source),sequence_sha256=digest(sequence),data_sha256=digest(out/'demonstrations.npz'),
              supervision='scripted_demonstration',game_ram_edits=False,
              limitation='Original per-frame button labels; policy deploys ten ready frames per action. Offline accuracy is not gameplay success.'))
    finally:env.close()

def clone(out,epochs,initial_policy=None,resume=None,stop_after=None):
    data=np.load(out/'demonstrations.npz');env=environment(out/'bc','approach')
    if 'control' in data.files:
        from control_context import ControlContext
        env=ControlContext(env)
    model=PPO.load(initial_policy,env=DummyVecEnv([lambda:env]),device='cpu') if initial_policy else model_for(env)
    obs={k:torch.as_tensor(data[k]) for k in env.observation_space.spaces};actions=torch.as_tensor(data['actions'],dtype=torch.long)
    optimizer=torch.optim.Adam(model.policy.parameters(),lr=3e-4)
    generator=torch.Generator().manual_seed(42)
    # Inverse square-root action-frequency weighting reduces long idle spans'
    # dominance without discarding the required waiting/dialogue labels.
    codes=actions[:,0]*4+actions[:,1];counts=torch.bincount(codes,minlength=20)
    weights=(counts[codes].float().clamp_min(1).rsqrt());weights/=weights.mean()
    history=[];start_epoch=0
    if resume:
        manifest=json.loads((resume/'manifest.json').read_text())
        if manifest['script_sha256']!=digest(Path(__file__)):raise ValueError('Supervised checkpoint script mismatch')
        for name,expected in manifest['artifacts'].items():
            if digest(resume/name)!=expected:raise ValueError('Supervised checkpoint integrity mismatch')
        saved=torch.load(resume/'training-state.pt',map_location='cpu')
        if saved['data_sha256']!=digest(out/'demonstrations.npz') or saved['target_epochs']!=epochs:
            raise ValueError('Supervised checkpoint data/horizon mismatch')
        restored=PPO.load(resume/'policy.zip',device='cpu')
        model.policy.load_state_dict(restored.policy.state_dict());del restored
        optimizer.load_state_dict(saved['optimizer']);generator.set_state(saved['shuffle_rng'])
        torch.set_rng_state(saved['torch_rng']);start_epoch=saved['epoch'];history=saved['history']
    try:
        for epoch in range(start_epoch, min(epochs,stop_after or epochs)):
            model.policy.set_training_mode(True);total=0
            for idx in torch.randperm(len(actions),generator=generator).split(128):
                _,logp,_=model.policy.evaluate_actions({k:v[idx] for k,v in obs.items()},actions[idx])
                loss=-(logp*weights[idx]).mean();optimizer.zero_grad();loss.backward()
                torch.nn.utils.clip_grad_norm_(model.policy.parameters(),1);optimizer.step();total+=float(loss.detach())*len(idx)
            history.append({'epoch':epoch+1,'weighted_nll':total/len(actions)})
            if (epoch+1)%10==0:
                checkpoint=out/'bc-checkpoints'/f'{epoch+1:04}'
                checkpoint.mkdir(parents=True,exist_ok=False)
                model.save(checkpoint/'policy.zip')
                torch.save({'optimizer':optimizer.state_dict(),'torch_rng':torch.get_rng_state(),
                            'shuffle_rng':generator.get_state(),'epoch':epoch+1,'target_epochs':epochs,
                            'history':history,'data_sha256':digest(out/'demonstrations.npz')},checkpoint/'training-state.pt')
                write(checkpoint/'manifest.json',{'boundary':'after_supervised_epoch',
                      'artifacts':{p.name:digest(p) for p in checkpoint.iterdir()},
                      'script_sha256':digest(Path(__file__))})
                print('BC',history[-1],flush=True)
        model.policy.set_training_mode(False)
        with torch.no_grad():
            predicted=torch.cat([model.policy._predict({k:v[idx] for k,v in obs.items()},deterministic=True)
                                 for idx in torch.arange(len(actions)).split(128)])
        write(out/'cloning.json',dict(supervision='behavior_cloning_scripted_route',epochs=history,
                                    training_action_accuracy=float((predicted==actions).all(dim=1).float().mean()),
                                    held_out_demonstrations=False,completed_epochs=len(history),target_epochs=epochs))
        model.save(out/'imitation-policy.zip')
    finally:env.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['capture','clone','evaluate']);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--policy',type=Path);p.add_argument('--tag',default='policy');p.add_argument('--epochs',type=int,default=50);p.add_argument('--resume-bc',type=Path);p.add_argument('--stop-after',type=int)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True);torch.set_num_threads(4)
    if args.mode=='capture':capture(args.out)
    elif args.mode=='clone':clone(args.out,args.epochs,resume=args.resume_bc,stop_after=args.stop_after)
    else:
        if args.policy:model=PPO.load(args.policy,device='cpu')
        else:
            env=environment(args.out/'untrained','house');model=model_for(env);env.close()
        evaluate(args.out,model,args.tag)
