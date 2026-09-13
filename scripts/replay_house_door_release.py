"""Verify a released house route from its original state, without intermediate loads."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.battle_ready_endpoint import require_battle_ready
from gameboy_agent.world_memory import file_hash
from run_toadstool_progression import apply


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', default='runs/house-door-teacher-qualification-v27/fresh-house-00')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    run = ROOT / args.run
    continuation = json.loads((run / 'continuation.json').read_text())
    for path, digest in continuation['sha256'].items():
        if file_hash(ROOT / path) != digest:
            raise RuntimeError(f'Artifact hash mismatch: {path}')
    start = continuation['start']
    env = ProgressionEnv(ROOT / start['rom'], ROOT / start['initial_state'],
                         max_steps=30000, max_frames=150000, completion_milestone=None)
    normalize = lambda value: json.loads(json.dumps(value))
    commands = 0
    try:
        env.reset(seed=0)
        for segment in continuation['replay_segments']:
            with (ROOT / segment).open() as stream:
                for line in stream:
                    row = json.loads(line)
                    info = apply(env, row['command'])[4]
                    if (fingerprint(env) != row['fingerprint'] or env.frames != row['frame']
                            or normalize(snapshot(env.pyboy)) != row['after']
                            or info['events'] != row['events']):
                        raise RuntimeError(f'Replay mismatch at command {commands}')
                    if snapshot(env.pyboy)['room'] == [1, 0, 6]:
                        raise RuntimeError('Boss room entered')
                    commands += 1
        if normalize(env.journal.state()) != json.loads((run / 'journal.json').read_text()):
            raise RuntimeError('Journal mismatch')
        final = require_battle_ready(env)
        m = env.pyboy.memory
        if not m[0xD90B] & 4 or m[0xC188]:
            raise RuntimeError('Boss door is not open and settled')
        result = dict(success=True, exact_replay=True, commands=commands, frames=env.frames,
                      final=final, door_open=True, door_animation=0, boss_room_entered=False,
                      intermediate_state_loads=0, source_run=args.run)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
        print(json.dumps(result), flush=True)
    finally:
        env.close()


if __name__ == '__main__':
    main()
