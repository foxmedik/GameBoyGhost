"""Bounded sequential experiment batch, with separate no-learning evaluations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv-ladx/bin/python'


def publish(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def evaluate(checkpoint, output, episode_steps=2048, untrained=False):
    import random
    import numpy as np
    import torch
    sys.path.insert(0, str(ROOT/'src'))
    from gameboy_agent.checkpoint import restore_checkpoint
    torch.set_num_threads(4)
    rom = output.parent/'evaluation.gbc'
    shutil.copy2(next(ROOT.glob('*.gbc')), rom)
    model, env, _ = restore_checkpoint(checkpoint, rom)
    results = []
    try:
        if untrained:
            from stable_baselines3 import PPO
            model = PPO('MultiInputPolicy',model.get_env(),seed=0,device='cpu',
                        policy_kwargs=model.policy_kwargs)
        env.config['max_steps'] = episode_steps
        # Same frozen start and sampling seeds for every candidate. These are
        # repeatable evaluation episodes, not unseen-game generalization.
        for deterministic, seed in [(True,10000),(False,10001),(False,10002),(False,10003)]:
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
            obs, _ = env.reset(seed=seed)
            reward_sum = 0.0; rooms = set(); sword_start = int(env.pyboy.memory[0xDB4E])
            max_sword = sword_start
            for step in range(episode_steps):
                action, _ = model.predict(obs, deterministic=deterministic)
                obs, reward, terminated, truncated, info = env.step(action)
                reward_sum += reward
                rooms.add(tuple(info['phase']['room']))
                # Pure read of wSwordLevel, verified in matching ROM symbols.
                max_sword = max(max_sword, int(env.pyboy.memory[0xDB4E]))
                if terminated or truncated: break
            results.append(dict(seed=seed, deterministic=deterministic, steps=step+1,
                                reward=reward_sum, rooms=len(rooms), death=bool(info.get('death',terminated)),
                                starting_sword_level=sword_start, max_sword_level=max_sword,
                                sword_acquired=sword_start==0 and max_sword>0))
        publish(output, dict(checkpoint=str(checkpoint), episodes=results,
                             harness_privilege='D', completion_evaluated=False,
                             learning_enabled=False, untrained_control=untrained, evaluation_start='checkpoint_initial_state',
                             sword_curriculum=env.sword_curriculum))
    finally:
        env.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--evaluate', type=Path)
    p.add_argument('--untrained',action='store_true')
    p.add_argument('--episode-steps', type=int, default=2048)
    args = p.parse_args()
    if args.evaluate:
        evaluate(args.evaluate, args.directory/('evaluation-untrained.json' if args.untrained else 'evaluation.json'), args.episode_steps, args.untrained)
        return
    batch = args.directory.resolve(); batch.mkdir(parents=True, exist_ok=False)
    plan = [(seed, entropy) for seed in range(3) for entropy in (0.01,0.03)]
    if args.smoke: plan = plan[:2]
    steps = 256 if args.smoke else 524288
    state = dict(batch_id=str(uuid.uuid4()), status='running', started_at=time.time(),
                 pid=os.getpid(), total_planned_steps=steps*len(plan), runs=[],
                 scope='six fixed-start assisted PPO runs; entropy comparison over three seeds',
                 completion_evaluated=False, wall_budget_hours=8)
    deadline = time.monotonic()+8*3600
    publish(batch/'status.json',state)
    # Preserve the exact launch scripts independently of later workspace edits.
    for script in ('train_ladx.py','overnight_batch.py'):
        shutil.copy2(ROOT/'scripts'/script,batch/script)
    state['script_hashes'] = {name:hashlib.sha256((batch/name).read_bytes()).hexdigest()
                             for name in ('train_ladx.py','overnight_batch.py')}
    for index, (seed, entropy) in enumerate(plan):
        if time.monotonic()>=deadline or shutil.disk_usage(ROOT).free < 20*1024**3:
            state['status']='stopped_at_resource_limit'; break
        entry = dict(index=index,seed=seed,entropy=entropy,target_steps=steps,status='training')
        state['runs'].append(entry); publish(batch/'status.json',state)
        logfile = batch/f'run-{index}.log'
        command = [str(PYTHON),str(ROOT/'scripts/train_ladx.py'),'--steps',str(steps),
                   '--seed',str(seed),'--entropy',str(entropy),'--checkpoint-every',
                   '128' if args.smoke else '32768']
        entry['command']=command
        try:
            with logfile.open('x') as log:
                result = subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                offset = 0
                tail = ''
                try:
                    while result.poll() is None:
                        time.sleep(1 if args.smoke else 10)
                        with logfile.open() as reader:
                            reader.seek(offset); chunk = reader.read(); offset = reader.tell()
                        tail = (tail + chunk)[-65536:]
                        if 'Exception ignored in:' in tail or 'Traceback (most recent call last)' in tail:
                            raise RuntimeError('Emulator/runtime traceback detected; candidate stopped')
                        if time.monotonic() >= deadline:
                            raise TimeoutError('Batch wall-clock budget exhausted')
                        if shutil.disk_usage(ROOT).free < 20*1024**3:
                            raise RuntimeError('Free disk below 20 GiB')
                finally:
                    if result.poll() is None:
                        result.terminate()
                        try: result.wait(timeout=10)
                        except subprocess.TimeoutExpired: result.kill(); result.wait()
            entry['returncode']=result.returncode
            run_lines = [line[4:] for line in logfile.read_text().splitlines() if line.startswith('RUN ')]
            if run_lines: entry['run_directory']=run_lines[-1]
            if result.returncode: raise RuntimeError(f'Training exited {result.returncode}; see {logfile}')
            run = Path(entry['run_directory'])
            result_data = json.loads((run/'result.json').read_text())
            entry['checkpoint']=result_data['latest_checkpoint']
            entry['training_summary']={k:result_data[k] for k in
                                      ('episodes_completed','deaths','rooms_seen','recent_episodes')}
            entry['status']='evaluating'; publish(batch/'status.json',state)
            with (batch/f'eval-{index}.log').open('x') as log:
                subprocess.run([str(PYTHON),str(ROOT/'scripts/overnight_batch.py'),
                                '--directory',str(run),'--evaluate',entry['checkpoint'],
                                '--episode-steps','32' if args.smoke else '2048'],
                               cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,
                               timeout=max(1,deadline-time.monotonic()))
            entry['evaluation']=json.loads((run/'evaluation.json').read_text())
            entry['status']='completed'
        except Exception as exc:
            entry['status']='failed'; entry['error']=repr(exc)
        publish(batch/'status.json',state)
    if state['status']=='running':
        state['status']='completed' if all(r['status']=='completed' for r in state['runs']) else 'completed_with_failures'
    state['finished_at']=time.time()
    publish(batch/'status.json',state)
    print(json.dumps(state),flush=True)


if __name__=='__main__': main()
