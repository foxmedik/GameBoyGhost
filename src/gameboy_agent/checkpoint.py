"""Verified local checkpoints at PPO update boundaries.

Pickled artifacts must be locally produced/trusted. Restore uses episode replay
to reconstruct PyBoy host state before restoring Python-side experiment state.
"""
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import pickle
import random
import shutil
from pathlib import Path

import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from gameboy_agent.training_env import TrainingEnv


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(env):
    h = hashlib.sha256(env.pyboy.screen.ndarray.tobytes())
    h.update(bytes(env.pyboy.memory[0xC000:0xE000]))
    for key in sorted(env.cached_observation):
        h.update(env.cached_observation[key].tobytes())
    return h.hexdigest()


def dump(path, value):
    with Path(path).open('wb') as f:
        pickle.dump(value, f, protocol=5)


def read(path):
    with Path(path).open('rb') as f:
        return pickle.load(f)


def save_checkpoint(destination, model, env, *, experiment_state):
    """Publish only after a whole optimizer update; no partial-rollout resume."""
    if str(model.device) != 'cpu':
        raise ValueError('This verified checkpoint path currently supports CPU training only')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    attrs = deepcopy({k:v for k,v in vars(env).items() if k != 'pyboy'})
    dump(destination/'environment.pkl', attrs)
    with (destination/'emulator.state').open('wb') as f:
        env.pyboy.save_state(f)
    shutil.copy2(env.init_state, destination/'initial.state')
    model.save(destination/'policy.zip')  # SB3 includes policy.optimizer.
    dump(destination/'rng.pkl', {'python':random.getstate(), 'numpy':np.random.get_state(),
                                 'torch':torch.get_rng_state()})
    vec = model.get_env()
    dump(destination/'vector.pkl', {k:deepcopy(getattr(vec,k)) for k in
          ['buf_obs','buf_dones','buf_rews','buf_infos','reset_infos','_seeds','_options']})
    (destination/'experiment.json').write_text(json.dumps(experiment_state,indent=2)+'\n')
    source_root = Path(__file__).parent
    manifest = {'schema_version':'ppo-boundary-checkpoint-v1', 'num_timesteps':model.num_timesteps,
                'rom_hash':digest(env.config['gb_path']), 'fingerprint':fingerprint(env),
                'episode_replay_steps':len(env.episode_actions),
                'restore_method':'verified_episode_replay_then_python_state',
                'checkpoint_boundary':'after_optimizer_update',
                'torch_threads':torch.get_num_threads(),
                'versions':{p:importlib.metadata.version(p) for p in
                            ['pyboy','torch','numpy','stable-baselines3','gymnasium']},
                'artifacts':{p.name:digest(p) for p in destination.iterdir() if p.is_file()},
                'sources':{p.name:digest(p) for p in source_root.glob('*.py')}}
    # Written last: a directory without this manifest is not a usable checkpoint.
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def restore_checkpoint(directory, rom):
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_text())
    for package, expected in manifest['versions'].items():
        if importlib.metadata.version(package) != expected:
            raise ValueError(f'Checkpoint dependency mismatch: {package}')
    torch.set_num_threads(manifest['torch_threads'])
    for name, expected in manifest['artifacts'].items():
        if digest(directory/name) != expected:
            raise ValueError(f'Checkpoint integrity mismatch: {name}')
    for name, expected in manifest['sources'].items():
        if digest(Path(__file__).parent/name) != expected:
            raise ValueError(f'Checkpoint code mismatch: {name}')
    if digest(rom) != manifest['rom_hash']:
        raise ValueError('Checkpoint ROM mismatch')
    attrs = read(directory/'environment.pkl')
    env = TrainingEnv(Path(rom), directory/'initial.state', max_steps=attrs['config']['max_steps'],
                      sword_curriculum=attrs.get('sword_curriculum',False))
    try:
        env.reset(seed=attrs['episode_seed'])
        for action in attrs['episode_actions']:
            env.step(np.asarray(action))
        if fingerprint(env) != manifest['fingerprint']:
            raise ValueError('Checkpoint episode replay fingerprint mismatch')
        vars(env).update(attrs)
        env.config = deepcopy(attrs['config'])
        env.config['gb_path'] = str(Path(rom).resolve())
        env.config['init_state'] = str((directory/'initial.state').resolve())
        env.init_state = env.config['init_state']
        vec = DummyVecEnv([lambda:env])
        for key,value in read(directory/'vector.pkl').items():
            setattr(vec,key,value)
        model = PPO.load(directory/'policy.zip',env=vec,device='cpu',force_reset=False)
        rng = read(directory/'rng.pkl')
        random.setstate(rng['python'])
        np.random.set_state(rng['numpy'])
        torch.set_rng_state(rng['torch'])
        return model, env, json.loads((directory/'experiment.json').read_text())
    except BaseException:
        env.close()
        raise
