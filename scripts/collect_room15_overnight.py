"""Frozen continuous-route diagnostic collection; never trains or selects a model."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.tail_cave_progression import execute_compass_room
from gameboy_agent.transitions import BUTTONS
from gameboy_agent.world_memory import file_hash
from run_toadstool_progression import Trace, apply


def write(path, obj):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(obj, indent=2)+'\n')
    temporary.replace(path)


def normalized(obj):
    return json.loads(json.dumps(obj))


def senses(env):
    m = env.pyboy.memory
    return {'state': snapshot(env.pyboy), 'frame': env.frames,
            'entities': [dict(slot=i, type=int(m[0xC3A0+i]), status=int(m[0xC280+i]),
                              state=int(m[0xC290+i]), x=int(m[0xC200+i]), y=int(m[0xC210+i]),
                              vx=int(m[0xC240+i]), vy=int(m[0xC250+i]), z=int(m[0xC310+i]))
                         for i in range(16) if m[0xC280+i]]}


def prefix(env, source):
    for line in (source/'trajectory.jsonl').open():
        row = json.loads(line)
        info = apply(env, row['command'])[4]
        if (fingerprint(env) != row['fingerprint'] or env.frames != row['frame']
                or normalized(snapshot(env.pyboy)) != row['after'] or info['events'] != row['events']):
            raise RuntimeError(f'Continuous prefix mismatch at {row["decision"]}')


def run_case(out, spec, plan):
    source = ROOT/plan['source']/f'development-house-{spec["base"]:02d}'
    dest = out/spec['id']
    dest.mkdir(exist_ok=False)
    def make():
        return ProgressionEnv(source/'game.gbc', source/'initial.state', max_steps=16000,
                              max_frames=300000, completion_milestone=None)
    rows, evidence = [], []
    env = make()
    began = time.monotonic()
    failure = None
    try:
        env.reset(seed=0)
        prefix(env, source)
        initial = senses(env)
        damage_before = env.journal.damage_raw
        healing_before = env.journal.healing_raw
        with (dest/'trajectory.jsonl').open('x') as stream, (dest/'observations.jsonl').open('x') as observations:
            class ObservedTrace(Trace):
                def record(self, method, *args, **kwargs):
                    observations.write(json.dumps(senses(self.env))+'\n')
                    return super().record(method, *args, **kwargs)
            traced = ObservedTrace(env, stream, rows)
            try:
                if spec['idle']:
                    traced.step_input_events(release=BUTTONS, frames=spec['idle'])
                execute_compass_room(traced, evidence)
            except Exception as exc:
                failure = f'{type(exc).__name__}: {exc}'
            final = senses(env)
            observations.write(json.dumps(final)+'\n')
        env.pyboy.screen.image.save(dest/'final.png')
        journal = normalized(env.journal.state())
        damage = env.journal.damage_raw-damage_before
        healing = env.journal.healing_raw-healing_before
    finally:
        env.close()
    replay = make()
    try:
        replay.reset(seed=0)
        prefix(replay, source)
        for row in rows:
            info = apply(replay, row['command'])[4]
            assert fingerprint(replay) == row['fingerprint']
            assert normalized(snapshot(replay.pyboy)) == normalized(row['after'])
            assert replay.frames == row['frame'] and info['events'] == row['events']
        assert normalized(replay.journal.state()) == journal
    finally:
        replay.close()
    result = dict(spec=spec, success=failure is None, failure=failure, initial=initial, final=final,
                  damage_raw=damage, healing_raw=healing, exact_replay=True, commands=len(rows),
                  control='teacher_only_room15', teacher_action_fraction=1.0,
                  autonomous_room15_evaluated=False, training_eligible=False,
                  seconds=round(time.monotonic()-began, 2))
    write(dest/'evidence.json', evidence)
    write(dest/'result.json', result)
    write(dest/'manifest.json', {p.name:file_hash(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({k:result[k] for k in ('spec','success','failure','damage_raw','seconds')}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    out = ROOT/plan['output']
    out.mkdir(exist_ok=False)
    write(out/'plan.json', plan)
    results = []
    try:
        for spec in plan['cases']:
            for name, digest in plan['frozen_inputs'].items():
                if file_hash(ROOT/name) != digest:
                    raise RuntimeError(f'Frozen input changed: {name}')
            results.append(run_case(out, spec, plan))
            write(out/'summary.json', dict(status='running', cases=len(results), planned=len(plan['cases']),
                  successes=sum(r['success'] for r in results), exact_replays=len(results),
                  total_commands=sum(r['commands'] for r in results), validation_loaded=False,
                  training_started=False, results=results))
        summary = json.loads((out/'summary.json').read_text())
        summary['status'] = 'complete'
        write(out/'summary.json', summary)
    except BaseException as exc:
        write(out/'failure.json', dict(error=f'{type(exc).__name__}: {exc}', completed=len(results)))
        raise


if __name__ == '__main__':
    main()
