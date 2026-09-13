"""Replay existing House-to-Door development evidence without extending it.

No controller exploration, teacher labeling, training or evaluation panels.
Only the two named development handoffs are accepted by this closeout tool.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.world_memory import file_hash
from run_toadstool_progression import apply

HANDOFFS = [
    'runs/full-health-worm-guard-v1/room0e-full-health-continuation.json',
    'runs/tail-cave-room10-state-check-v2/continuation.json',
]


def verify(path):
    handoff = json.loads((ROOT / path).read_text())
    for source, expected in handoff['sha256'].items():
        if file_hash(ROOT / source) != expected:
            raise ValueError(f'Changed handoff dependency: {source}')
    rows = [json.loads(line) for source in handoff['replay_segments']
            for line in (ROOT / source).read_text().splitlines()]
    assert [r['decision'] for r in rows] == list(range(len(rows))), 'Noncontiguous commands'
    env = ProgressionEnv(ROOT / handoff['start']['rom'], ROOT / handoff['start']['initial_state'],
        max_steps=len(rows) + 100, max_frames=rows[-1]['frame'] + 1000, completion_milestone=None)
    try:
        env.reset(seed=0)
        for index, row in enumerate(rows):
            info = apply(env, row['command'])[4]
            actual = json.loads(json.dumps(snapshot(env.pyboy)))
            assert fingerprint(env) == row['fingerprint'], f'Fingerprint mismatch {index}'
            assert actual == row['after'], f'Snapshot mismatch {index}'
            assert env.frames == row['frame'], f'Frame mismatch {index}'
            assert info['events'] == row['events'], f'Events mismatch {index}'
            if index % 3000 == 0:
                print(f'{path}: {index}/{len(rows)} commands verified', flush=True)
        assert actual == handoff['final']['state'], 'Final snapshot mismatch'
        assert env.frames == handoff['final']['frame'], 'Final frame mismatch'
        assert int(env.pyboy.memory[0xDB94]) == handoff['final'].get('pending_damage', 0)
        items = list(env.pyboy.memory[0xDBCC:0xDBD1])
        if 'dungeon_items' in handoff['final']:
            assert items == handoff['final']['dungeon_items'], 'Dungeon items mismatch'
        return dict(handoff=path, handoff_sha256=file_hash(ROOT / path),
            dependencies_hashed=len(handoff['sha256']), commands=len(rows), exact_replay=True,
            final_frame=env.frames, final=actual, dungeon_items=items,
            pending_damage=int(env.pyboy.memory[0xDB94]),
            extra_progression_commands=0, training_labels=0, midroute_state_loads=0)
    finally:
        env.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Never overwrite an earlier verification record.
    with args.output.open('x') as stream:
        results = [verify(path) for path in HANDOFFS]
        json.dump(dict(schema='house-door-handoff-verification-v1',
            verifier_sha256=file_hash(Path(__file__)), sealed_validation_used=False,
            checks=['dependency hashes', 'all command fingerprints', 'all snapshots',
                    'all frame counts', 'all emitted events', 'final state and dungeon items'],
            results=results), stream, indent=2)
        stream.write('\n')
    print('Both existing continuous handoffs verified; zero extension commands.', flush=True)


if __name__ == '__main__':
    main()
