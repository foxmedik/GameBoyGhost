"""Verify a complete physical house-to-door replay, including live endpoint RAM."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from gameboy_agent.battle_ready_endpoint import require_battle_ready
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.world_memory import file_hash
from run_toadstool_progression import apply


def verify(path):
    h = json.loads(path.read_text())
    for name, expected in h['sha256'].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError(f'Changed dependency: {name}')
    rows = [json.loads(line) for name in h['replay_segments']
            for line in (ROOT / name).read_text().splitlines()]
    if [r['decision'] for r in rows] != list(range(len(rows))):
        raise ValueError('Commands are not contiguous from house decision zero')
    if file_hash(ROOT / h['start']['rom']) != '6285ba6201f17bc8595c600ebc2477d52561f0aff29b11f7fc3343bacb2e230b':
        raise ValueError('ROM does not match the frozen project ROM')
    env = ProgressionEnv(ROOT / h['start']['rom'], ROOT / h['start']['initial_state'],
        max_steps=len(rows)+100, max_frames=rows[-1]['frame']+1000, completion_milestone=None)
    try:
        env.reset(seed=0)
        m = env.pyboy.memory
        if m[0xD90B] & 4 or snapshot(env.pyboy)['sword']:
            raise ValueError('Start already has an open boss door or sword')
        opened_at = None
        for index, row in enumerate(rows):
            was_open = bool(m[0xD90B] & 4)
            info = apply(env, row['command'])[4]
            actual = json.loads(json.dumps(snapshot(env.pyboy)))
            if (fingerprint(env) != row['fingerprint'] or actual != row['after']
                    or env.frames != row['frame'] or info['events'] != row['events']):
                raise ValueError(f'Exact replay mismatch at command {index}')
            if actual['room'] == [1, 0, 6]:
                raise ValueError('Forbidden boss-room entry')
            if not was_open and m[0xD90B] & 4:
                if actual['room'] != [1, 0, 11] or not m[0xDBCF]:
                    raise ValueError('Opening transition occurred outside the required context')
                opened_at = env.frames
            if index % 3000 == 0:
                print(f'{index}/{len(rows)} commands verified', flush=True)
        final = json.loads(json.dumps(require_battle_ready(env)))
        if opened_at is None or not m[0xD90B] & 4 or m[0xC188] or m[0xC18C] or m[0xC18D]:
            raise ValueError('Door transition absent or shutters unsettled at finish')
        if rows[-1]['command'].get('buttons') != []:
            raise ValueError('Final command did not release all buttons')
        if final != h['final']['state'] or env.frames != h['final']['frame']:
            raise ValueError('Final handoff differs')
        items = list(m[0xDBCC:0xDBD1])
        if items != h['final']['dungeon_items']:
            raise ValueError('Final dungeon items differ')
        return dict(exact_replay=True, commands=len(rows), final_frame=env.frames,
            opened_frame=opened_at, final=final, dungeon_items=items,
            door_status=int(m[0xD90B]), door_animation=int(m[0xC188]),
            pending_healing=int(m[0xDB93]), pending_damage=int(m[0xDB94]),
            grounded=not m[0xFFA2] and not m[0xC11C], movement_released=True,
            forbidden_boss_room_entered=False, midroute_state_loads=0,
            control='guided_physical_development', teacher_qualified=False,
            sealed_validation_used=False, training_labels=0,
            handoff_sha256=file_hash(path), verifier_sha256=file_hash(Path(__file__)))
    finally:
        env.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--handoff', type=Path, default=ROOT/'runs/house-nightmare-door-proof-v1/continuation.json')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    with a.output.open('x') as stream:
        try:
            result = verify(a.handoff)
        except Exception as exc:
            json.dump(dict(exact_replay=False, error=f'{type(exc).__name__}: {exc}'), stream, indent=2)
            stream.write('\n')
            raise
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print('Full-health house-to-open-door proof verified.', flush=True)
