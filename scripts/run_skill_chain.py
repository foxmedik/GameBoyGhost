"""Learned sword skill -> scripted novelty exploration, with verified replay.

No tail-key/credits success is inferred from exploration reward or room count.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
import socket
import sys
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from gameboy_agent.checkpoint import digest, fingerprint
from gameboy_agent.skills import Senses, SequentialPlanner
from gameboy_agent.training_env import TrainingEnv
from control_context import ControlContext
from sword_imitation import STARTS, write
from tree_controller import features, predict


def senses(base):
    m = base.pyboy.memory
    return Senses(tuple(int(m[a]) for a in (0xDBA5, 0xFFF7, 0xFFF6)),
                  int(m[0xFF98]), int(m[0xFF99]), bool(m[0xC19F]),
                  bool(m[0xDB4E]), int(m[0xDB5A]), int(m[0xDB01]), int(m[0xDB00]))


class SwordController:
    def __init__(self, env, policy):
        self.env, self.policy = env, policy

    def action(self, state):
        obs = self.env.observation(self.env.unwrapped.cached_observation)
        return predict(self.policy, features(obs)).tolist()


def source_hashes():
    files = list((ROOT / 'src/gameboy_agent').glob('*.py'))
    files += [ROOT / 'scripts' / name for name in
              ('run_skill_chain.py', 'control_context.py', 'sword_imitation.py', 'tree_controller.py')]
    files += list((ROOT / 'references/LADXExperiments/experiments').rglob('*.py'))
    return {str(p.relative_to(ROOT)): digest(p) for p in files}


def versions():
    return {p: importlib.metadata.version(p) for p in
            ('pyboy', 'numpy', 'gymnasium', 'torch', 'stable-baselines3')}


def run(out, *, start='house', explore_steps=2000, stop_after=None, resume=None, seed=0):
    out = Path(out).resolve()
    if explore_steps < 1 or (stop_after is not None and stop_after < 1):
        raise ValueError('Budgets must be positive')
    saved = None
    if resume:
        resume = Path(resume).resolve()
        manifest = json.loads((resume / 'manifest.json').read_text())
        if manifest['sources'] != source_hashes() or manifest['versions'] != versions():
            raise ValueError('Checkpoint source/dependency mismatch')
        for name, sha in manifest['artifacts'].items():
            if digest(resume / name) != sha:
                raise ValueError('Checkpoint artifact mismatch')
        saved = json.loads((resume / 'checkpoint.json').read_text())
        if saved['status'] != 'paused':
            raise ValueError('Only a paused chain can be resumed')
        start, seed, explore_steps = saved['start'], saved['seed'], saved['explore_budget']
        if stop_after is not None and stop_after <= len(saved['actions']):
            raise ValueError('Stop must exceed saved step')
        state_path, policy_path = resume / 'initial.state', resume / 'policy.json'
    else:
        selection = json.loads((ROOT / 'configs/sword_controller.json').read_text())
        policy_path, state_path = ROOT / selection['policy_path'], STARTS[start]
        if digest(policy_path) != selection['policy_sha256']:
            raise ValueError('Selected controller integrity mismatch')
    rom_path = next(ROOT.glob('*.gbc'))
    if saved and digest(rom_path) != manifest['rom_sha256']:
        raise ValueError('Checkpoint ROM mismatch')
    out.mkdir(parents=True, exist_ok=False)
    for source, name in ((rom_path, 'game.gbc'), (state_path, 'initial.state'), (policy_path, 'policy.json')):
        shutil.copy2(source, out / name)
    policy = json.loads((out / 'policy.json').read_text())
    # Disable the curriculum's sword termination from the beginning, so the
    # handoff requires no reset, teleport, or mutation of a terminal episode.
    base = TrainingEnv(out / 'game.gbc', out / 'initial.state',
                       max_steps=1600 + explore_steps + 1, sword_curriculum=False)
    env = ControlContext(base)
    planner = SequentialPlanner(SwordController(env, policy), explore_budget=explore_steps)
    actions, rooms, post_rooms = [], set(), set()
    run_id = str(uuid.uuid4())
    episode_id = saved['episode_id'] if saved else str(uuid.uuid4())
    status, failure = 'paused', None
    try:
        env.reset(seed=seed)
        def take(action):
            before = senses(base)
            _, reward, done, truncated, info = env.step(np.asarray(action))
            after = senses(base)
            rooms.add(after.room)
            if planner.index == 1:
                post_rooms.add(after.room)
            actions.append(action)
            return dict(step=len(actions) - 1, action=action, skill=planner.skills[planner.index].name,
                        before=before.__dict__, after=after.__dict__, reward=reward,
                        reward_components=info['reward'], phase=info['phase'],
                        terminated=done, truncated=truncated)

        if saved:
            for expected in saved['actions']:
                action = planner.action(senses(base), len(actions))
                if action != expected:
                    raise ValueError('Planner replay action mismatch')
                take(action)
            if (fingerprint(base) != saved['fingerprint'] or planner.state() != saved['planner']):
                raise ValueError('Checkpoint environment/planner replay mismatch')
        prefix_steps = len(actions)
        with (out / 'trajectory.jsonl').open('x') as log:
            while stop_after is None or len(actions) < stop_after:
                current = senses(base)
                rooms.add(current.room)
                action = planner.action(current, len(actions))
                if action is None:
                    status = planner.events[-1]['status']
                    break
                row = take(action)
                row.update(schema='skill-chain-step-v1', run_id=run_id, episode_id=episode_id,
                           producer_id=socket.gethostname(), harness_privilege='D',
                           supervision='learned_imitation' if planner.index == 0 else 'scripted_exploration')
                log.write(json.dumps(row) + '\n')
                if row['terminated'] or row['truncated']:
                    status = 'failed_death' if senses(base).health == 0 else 'environment_truncated'
                    planner.events.append(dict(step=len(actions), skill=planner.skills[planner.index].name,
                                               status=status, steps=planner.skills[planner.index].steps))
                    break
    except Exception as exc:
        status, failure = 'failed_exception', repr(exc)
        raise
    finally:
        result = dict(schema='skill-chain-checkpoint-v1', run_id=run_id, episode_id=episode_id,
                      producer_id=socket.gethostname(), start=start, seed=seed,
                      parent_checkpoint=str(resume) if resume else None,
                      explore_budget=explore_steps, actions=actions, steps=len(actions),
                      status=status, failure=failure, sword_acquired=senses(base).sword,
                      planner=planner.state(), fingerprint=fingerprint(base),
                      rooms=sorted(rooms), post_sword_rooms=sorted(post_rooms),
                      harness_privilege='D', planner_type='scripted_skill_sequence',
                      mode='development', human_intervened=False,
                      exploration_type='scripted_position_novelty', completion_evaluated=False,
                      tail_cave_evaluated=False)
        write(out / 'checkpoint.json', result)
        write(out / 'events.json', planner.events)
        with (out / 'emulator.state').open('xb') as stream:
            base.pyboy.save_state(stream)
        base.pyboy.screen.image.save(out / 'final.png')
        write(out / 'manifest.json', dict(schema='skill-chain-manifest-v1', sources=source_hashes(),
              versions=versions(), rom_sha256=digest(out / 'game.gbc'),
              restore_method='verified_actions_and_planner_replay',
              artifacts={p.name: digest(p) for p in out.iterdir() if p.is_file() and p.name != 'game.gbc'}))
        env.close()
    summary = {k: result[k] for k in ('steps', 'status', 'sword_acquired', 'rooms', 'post_sword_rooms')}
    summary['replayed_steps'] = prefix_steps
    print(json.dumps(summary), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path)
    parser.add_argument('--start', choices=list(STARTS), default='house')
    parser.add_argument('--explore-steps', type=int, default=2000)
    parser.add_argument('--stop-after', type=int)
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    run(args.out or ROOT / 'runs' / str(uuid.uuid4()), start=args.start,
        explore_steps=args.explore_steps, stop_after=args.stop_after, resume=args.resume, seed=args.seed)
