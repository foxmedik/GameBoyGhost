"""Frozen, replay-verified encounter takeover gate. No training or label export."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.room15_takeover import EncounterTakeover, BoundedInputs
from gameboy_agent.tail_cave_progression import enter_compass_room, clear_compass_room, GEL
from gameboy_agent.tail_cave_teacher import entities
from gameboy_agent.transitions import BUTTONS
from gameboy_agent.world_memory import file_hash
from collect_room15_overnight import prefix, senses, normalized, write
from run_toadstool_progression import Trace, apply


def verify_row(env, row, info):
    if (fingerprint(env) != row['fingerprint']
            or normalized(snapshot(env.pyboy)) != row['after']
            or env.frames != row['frame'] or info['events'] != row['events']):
        raise RuntimeError(f'exact replay mismatch at decision {row["decision"]}')


def run_case(out, spec, plan):
    source = ROOT / plan['source'] / f'development-house-{spec["base"]:02d}'
    dest = out / spec['id']
    dest.mkdir()
    old = []
    if plan['mode'] == 'local':
        old = [json.loads(line) for line in (ROOT / spec['trajectory']).read_text().splitlines()][:spec['prefix_count']]

    def make():
        return ProgressionEnv(source/'game.gbc', source/'initial.state', max_steps=16000,
                              max_frames=300000, completion_milestone=None)

    def setup(env):
        env.reset(seed=0)
        prefix(env, source)
        env.step_input_events(release=BUTTONS, frames=spec['idle'])
        for row in old:
            verify_row(env, row, apply(env, row['command'])[4])
        if old and (env.frames != spec['trigger_frame'] or fingerprint(env) != spec['trigger_fingerprint']):
            raise RuntimeError('frozen trigger mismatch')

    began = time.monotonic()
    env = make()
    rows, evidence = [], []
    failure = None
    initial = None
    damage_before = None
    try:
        setup(env)
        with (dest/'trajectory.jsonl').open('x') as stream:
            traced = Trace(env, stream, rows)
            if plan['mode'] == 'entry':
                enter_compass_room(traced, evidence)
            initial = senses(env)
            if initial['state']['health'] != spec['expected_health']:
                raise RuntimeError('actual start health differs from frozen case')
            damage_before = env.journal.damage_raw
            if plan['mode'] == 'local':
                EncounterTakeover().run(traced, evidence)
            elif plan['mode'] == 'entry':
                clear_compass_room(BoundedInputs(traced, max_commands=700), evidence)
            else:
                raise RuntimeError('unsupported gate mode')
            final = senses(env)
            if final['state']['room'] != [1,0,21] or not final['state']['health'] or entities(env, GEL):
                raise RuntimeError('room-clear contract failed')
    except Exception as exc:
        failure = f'{type(exc).__name__}: {exc}'
    finally:
        final = senses(env)
        journal = deepcopy(env.journal.state())
        damage = None if damage_before is None else env.journal.damage_raw - damage_before
        env.pyboy.screen.image.save(dest/'final.png')
        env.close()
    replay = make()
    replay_failure = None
    try:
        setup(replay)
        for row in rows:
            verify_row(replay, row, apply(replay, row['command'])[4])
        if replay.journal.state() != journal:
            raise RuntimeError('final replay journal mismatch')
    except Exception as exc:
        replay_failure = f'{type(exc).__name__}: {exc}'
    finally:
        replay.close()
    low = spec['expected_health'] == 4
    result = dict(spec=spec, success=failure is None, failure=failure, initial=initial,
                  final=final, damage_raw=damage, exact_replay=replay_failure is None,
                  replay_failure=replay_failure, commands=len(rows),
                  case_passed=failure is None and replay_failure is None and (not low or damage == 0),
                  control='deterministic_encounter_takeover' if old else 'qualified_teacher_from_room_entry',
                  autonomous_room15_evaluated=False, training_eligible=False,
                  seconds=round(time.monotonic()-began, 3))
    write(dest/'result.json', result)
    write(dest/'evidence.json', evidence)
    write(dest/'manifest.json', {p.name:file_hash(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({k:result[k] for k in ('spec','success','failure','damage_raw','exact_replay','seconds')}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    args.out.mkdir(exist_ok=False)
    shutil.copy2(args.plan, args.out/'plan.json')
    results = []
    started = time.monotonic()
    try:
        for spec in plan['cases']:
            for path, sha in plan['frozen_inputs'].items():
                if file_hash(ROOT/path) != sha:
                    raise RuntimeError(f'frozen artifact changed: {path}')
            if time.monotonic() - started > plan['max_execution_seconds']:
                raise RuntimeError('experiment execution budget expired')
            results.append(run_case(args.out, spec, plan))
            report = dict(status='running', cases=len(results), planned=len(plan['cases']),
                          successes=sum(r['success'] for r in results), exact_replays=sum(r['exact_replay'] for r in results),
                          half_heart_cases=sum(r['spec']['expected_health']==4 for r in results),
                          half_heart_zero_damage=sum(r['case_passed'] and r['spec']['expected_health']==4 for r in results),
                          gate_passed=False, validation_loaded=False, training_started=False,
                          autonomous_room15_evaluated=False, results=results,
                          execution_seconds=round(time.monotonic()-started, 3))
            write(args.out/'summary.json', report)
        report['status'] = 'complete'
        report['gate_passed'] = (all(r['case_passed'] for r in results)
                                 and report['half_heart_cases']==plan['required_half_heart_cases'])
        write(args.out/'summary.json', report)
    except Exception as exc:
        write(args.out/'failure.json', {'error':str(exc), 'cases_completed':len(results), 'gate_passed':False})
        raise


if __name__ == '__main__':
    main()
