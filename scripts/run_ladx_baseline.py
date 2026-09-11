"""Run a bounded, local LADX/SB3 smoke experiment from the project root."""
import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gameboy_agent.ladx_baseline import BaselineEnv, CustomFeatureExtractor, UPSTREAM
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.monitor import Monitor


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path)
    parser.add_argument('--steps', type=int, default=256)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    if args.steps < 64 or args.steps % 64:
        parser.error('--steps must be a positive multiple of 64')
    roms = list(ROOT.glob('*.gbc'))
    rom = args.rom.resolve() if args.rom else (roms[0] if len(roms) == 1 else None)
    if rom is None:
        parser.error('Specify --rom when the root does not contain exactly one GBC file')
    run_id = str(uuid.uuid4())
    run = ROOT / 'runs' / run_id
    run.mkdir(parents=True)
    shutil.copy2(rom, run / 'game.gbc')
    state = UPSTREAM / 'ladx.gbc.state'
    shutil.copy2(state, run / 'initial.state')
    config = dict(seed=args.seed, total_timesteps=args.steps, n_steps=64,
                  batch_size=32, n_epochs=2, learning_rate=0.00003,
                  gamma=0.996, vf_coef=0.5, ent_coef=0.01,
                  device='cpu', torch_threads=4, max_episode_steps=128,
                  harness_mode='reproduction',
                  curriculum='fixed_upstream_savestate', render_all_frames=True,
                  net_arch=[1024, 1024])
    metadata = dict(schema_version='baseline-smoke-v1', run_id=run_id,
                    producer_id=socket.gethostname(), game_id='zelda_ladx',
                    rom_hash=sha(rom), initial_state_hash=sha(state),
                    upstream_commit=subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip(),
                    config=config, config_hash=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),
                    source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__), ROOT/'src/gameboy_agent/ladx_baseline.py', ROOT/'src/gameboy_agent/rom_profile.py']},
                    hardware=platform.machine(), os_version=platform.platform(),
                    versions={p:importlib.metadata.version(p) for p in ['pyboy','torch','stable-baselines3','gymnasium','numpy']},
                    mode='training_smoke', harness_privilege='D',
                    human_intervention=False, completion_evaluated=False,
                    started_at=time.time(), status='running')
    def write_metadata():
        (run/'run.json').write_text(json.dumps(metadata,indent=2)+'\n')
    write_metadata()
    print(f'Run directory: {run}', flush=True)
    torch.set_num_threads(4)
    env = None
    try:
        env = BaselineEnv(run/'game.gbc', run/'initial.state', max_steps=128)
        check_env(env, warn=True, skip_render_check=True)
        print('Gym/SB3 environment checks passed', flush=True)
        actions = np.random.default_rng(args.seed).integers([0,0],[5,4],size=(16,2))
        traces=[]
        for _ in range(2):
            obs, _ = env.reset(seed=args.seed)
            trace=[]
            for action in actions:
                obs,reward,terminated,truncated,_ = env.step(action)
                digest=hashlib.sha256(b''.join(obs[k].tobytes() for k in sorted(obs))).hexdigest()
                trace.append([digest,reward,terminated,truncated])
                if terminated or truncated:
                    break
            traces.append(trace)
        assert traces[0] == traces[1], 'Fixed-start environment replay differs'
        metadata['replay_steps_verified']=len(traces[0])
        (run/'replay-check.json').write_text(json.dumps({'actions':actions.tolist(),'traces':traces},indent=2)+'\n')
        print('Fixed-start observation/reward replay check passed',flush=True)
        monitored = Monitor(env, str(run/'monitor.csv'))
        model = PPO('MultiInputPolicy', monitored, seed=args.seed, device='cpu',
                    n_steps=64, batch_size=32, n_epochs=2,
                    learning_rate=0.00003, gamma=0.996, vf_coef=0.5, ent_coef=0.01,
                    policy_kwargs=dict(features_extractor_class=CustomFeatureExtractor,
                                       net_arch=[1024,1024], activation_fn=torch.nn.ReLU),
                    verbose=1, tensorboard_log=str(run/'tensorboard'))
        before = [p.detach().clone() for p in model.policy.parameters()]
        started=time.monotonic()
        model.learn(total_timesteps=args.steps)
        metadata['training_seconds']=time.monotonic()-started
        assert all(torch.isfinite(p).all() for p in model.policy.parameters())
        assert any(not torch.equal(a,b) for a,b in zip(before,model.policy.parameters())), 'No weight update'
        model.save(run/'policy.zip')
        reloaded=PPO.load(run/'policy.zip',device='cpu')
        obs,_=env.reset(seed=args.seed)
        a,_=model.predict(obs,deterministic=True)
        b,_=reloaded.predict(obs,deterministic=True)
        assert np.array_equal(a,b), 'Loaded model predicts a different action'
        for _ in range(16):
            action,_=reloaded.predict(obs,deterministic=True)
            obs,_,term,trunc,_=env.step(action)
            if term or trunc:
                obs,_=env.reset(seed=args.seed)
        env.pyboy.screen.image.save(run/'screen.png')
        metadata.update(status='passed', training_steps=model.num_timesteps,
                        policy_hash=sha(run/'policy.zip'), model_reload_verified=True)
        print('Training, weight update, model reload, and 16-step inference passed',flush=True)
    except Exception as exc:
        metadata.update(status='failed',error=repr(exc))
        raise
    finally:
        if env is not None:
            env.close()
        metadata['finished_at']=time.time()
        write_metadata()


if __name__ == '__main__':
    main()
