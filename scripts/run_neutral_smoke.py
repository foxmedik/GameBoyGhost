"""Exercise physical controls without game-specific assistance or rewards."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import uuid

import numpy as np
from PIL import Image
from stable_baselines3.common.env_checker import check_env

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gameboy_agent.neutral_env import NeutralEnv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path)
    parser.add_argument('--state', type=Path, help='Omit for power-on start')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--steps', type=int, default=256)
    args = parser.parse_args()
    if args.steps < 1:
        parser.error('--steps must be positive')
    roms = list(ROOT.glob('*.gbc'))
    rom = args.rom.resolve() if args.rom else (roms[0] if len(roms) == 1 else None)
    if rom is None:
        parser.error('Specify --rom')
    run_id = str(uuid.uuid4())
    run = ROOT/'runs'/run_id
    run.mkdir(parents=True)
    shutil.copy2(rom, run/'game.gbc')
    data = rom.read_bytes()
    header_checksum = 0
    for byte in data[0x134:0x14D]:
        header_checksum = (header_checksum-byte-1) & 255
    global_checksum = (sum(data)-sum(data[0x14E:0x150])) & 65535
    report = dict(schema_version='neutral-smoke-v1', run_id=run_id,
                  mode='neutral', observation='rgb_framebuffer', reward='zero',
                  controls=list(NeutralEnv.buttons), frames_per_step=10,
                  seed=args.seed, steps=args.steps, completion_evaluated=False,
                  harness_privilege='A surface; completion detector pending',
                  start='savestate' if args.state else 'power_on',
                  rom_sha256=hashlib.sha256(data).hexdigest(),
                  rom_header=dict(title=data[0x134:0x143].rstrip(b'\0').decode('ascii',errors='replace'),
                                  revision=data[0x14C], cartridge_type=data[0x147],
                                  size_bytes=len(data),
                                  header_checksum_valid=header_checksum==data[0x14D],
                                  global_checksum_valid=global_checksum==int.from_bytes(data[0x14E:0x150],'big')),
                  rom_adapter_semantics_verified=False,
                  pyboy_version=importlib.metadata.version('pyboy'),
                  source_sha256=hashlib.sha256((ROOT/'src/gameboy_agent/neutral_env.py').read_bytes()).hexdigest(),
                  status='running')
    state = None
    if args.state:
        state = run/'initial.state'
        shutil.copy2(args.state, state)
        report['state_sha256']=hashlib.sha256(state.read_bytes()).hexdigest()
    env = None
    try:
        env = NeutralEnv(run/'game.gbc', state, max_steps=args.steps)
        check_env(env, warn=True, skip_render_check=True)
        env.reset(seed=args.seed)
        rng = np.random.default_rng(args.seed)
        with (run/'actions.jsonl').open('x') as output:
            for step in range(args.steps):
                action = rng.integers(0,2,8,dtype=np.int8)
                obs, reward, terminated, truncated, info = env.step(action)
                output.write(json.dumps(dict(step=step, buttons=action.tolist(),
                                 screen_sha256=hashlib.sha256(obs.tobytes()).hexdigest(),
                                 reward=reward, terminated=terminated, truncated=truncated))+'\n')
        Image.fromarray(obs).save(run/'screen.png')
        report['status']='passed'
    except Exception as exc:
        report.update(status='failed',error=repr(exc))
        raise
    finally:
        if env is not None:
            env.close()
        (run/'run.json').write_text(json.dumps(report,indent=2)+'\n')
        print(run)


if __name__ == '__main__':
    main()
