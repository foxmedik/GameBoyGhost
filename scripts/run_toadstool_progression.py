"""Record and independently replay scripted physical quest milestones."""
import argparse
from copy import deepcopy
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.world_memory import WorldMemory, file_hash
from gameboy_agent.toadstool_teacher import execute


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def apply(env, command):
    if command.get('timing') == 'emulated_frames':
        return env.step_input_events(command['buttons'], release=command['release'],
            frames=command['action_frames'], release_after=command['release_after'])
    return env.step_buttons(command['buttons'], action_frames=command['action_frames'],
                            legacy_action=command['legacy_action'])


class Trace:
    def __init__(self, env, stream, rows):
        self.env, self.stream, self.rows = env, stream, rows
        self.decision_limit = None

    def __getattr__(self, key):
        return getattr(self.env, key)

    def step_buttons(self, *args, **kwargs):
        return self.record(self.env.step_buttons, *args, **kwargs)

    def step_input_events(self, *args, **kwargs):
        return self.record(self.env.step_input_events, *args, **kwargs)

    def record(self, method, *args, **kwargs):
        if self.decision_limit is not None and self.env.total_steps >= self.decision_limit:
            raise RuntimeError('Progression extension decision budget exhausted')
        before = snapshot(self.env.pyboy)
        result = method(*args, **kwargs)
        row = dict(decision=self.env.total_steps-1, before=before,
            after=snapshot(self.env.pyboy), command=deepcopy(self.env.episode_actions[-1]),
            frame=self.env.frames, events=result[4]['events'], fingerprint=fingerprint(self.env))
        self.rows.append(row)
        self.stream.write(json.dumps(row)+'\n')
        self.stream.flush()
        if (result[2] or result[3]) and not result[4].get('task_success'):
            raise RuntimeError('Episode ended before the requested progression stage finished')
        return result


def run(out, stage='toadstool'):
    source = ROOT/'runs'/dict(toadstool='progression-forest-terrain-v5',
        **{'witch-approach':'progression-toadstool-v1',
           'witch-exchange':'progression-witch-approach-v4',
           'tarin':'progression-witch-exchange-v12',
           'tail-key':'progression-tarin-v3',
           'tail-cave':'progression-tail-key-v2'})[stage]
    manifest = json.loads((source/'manifest.json').read_text())
    for name, expected in manifest['artifacts'].items():
        if file_hash(source/name) != expected:
            raise ValueError(f'Prefix artifact mismatch: {name}')
    out.mkdir(parents=True, exist_ok=False)
    for name in ('game.gbc', 'initial.state'):
        shutil.copy2(source/name, out/name)
    write(out/'plan.json', dict(schema='toadstool-progression-v1', stage=stage, source=str(source),
        source_trace_sha256=file_hash(source/'trajectory.jsonl'),
        max_decisions=12288, max_frames=300000, optimizer_updates=0,
        assistance='scripted_known_route_with_source_grounded_rom_senses',
        extension_decision_budget=2048 if stage != 'toadstool' else None,
        criterion=('physical_toadstool_latch_alive_plus_exact_independent_action_replay'
                   if stage == 'toadstool' else 'physical_return_to_forest_or_first_blocker_plus_exact_replay'
                   if stage == 'witch-approach' else 'physical_tail_cave_entry_or_first_blocker_plus_exact_replay' if stage == 'tail-cave' else 'physical_tail_key_or_first_blocker_plus_exact_replay' if stage == 'tail-key' else 'physical_tarin_cure_or_first_blocker_plus_exact_replay' if stage == 'tarin'
                   else 'physical_witch_exchange_or_first_blocker_plus_exact_replay'),
        scope='teacher_baseline_not_learned_quest_success',
        rom_sha256=file_hash(out/'game.gbc'), initial_state_sha256=file_hash(out/'initial.state'),
        versions={p:importlib.metadata.version(p) for p in ('pyboy','numpy','torch')},
        code_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in
                     [Path(__file__), *sorted((ROOT/'src/gameboy_agent').glob('*.py'))]}))
    began = time.monotonic()
    rows, evidence = [], []
    env = ProgressionEnv(out/'game.gbc', out/'initial.state', max_steps=12288, max_frames=300000)
    status, failure = ('toadstool_acquired' if stage == 'toadstool' else 'returned_to_forest' if stage == 'witch-approach' else 'raccoon_cured' if stage == 'tarin' else 'tail_key_acquired' if stage == 'tail-key' else 'tail_cave_entered' if stage == 'tail-cave' else 'powder_acquired'), None
    with (out/'trajectory.jsonl').open('x') as stream:
        traced = Trace(env, stream, rows)
        try:
            env.reset(seed=0)
            prefix = [json.loads(line) for line in (source/'trajectory.jsonl').read_text().splitlines()]
            for old in prefix:
                apply(traced, old['command'])
                if rows[-1]['fingerprint'] != old['fingerprint']:
                    raise RuntimeError(f'Physical prefix changed at decision {old["decision"]}')
            if stage == 'toadstool' and (env.journal.damage_raw or env.journal.healing_raw):
                raise RuntimeError('Full-health forest regression failed')
            evidence.append(dict(kind='forest_prefix_exact' if stage == 'toadstool' else 'toadstool_prefix_exact',
                                 decisions=len(prefix), frame=env.frames))
            if stage == 'toadstool':
                execute(traced, evidence)
            else:
                traced.decision_limit = env.total_steps + 2048
                from gameboy_agent.witch_approach import execute as approach_witch
                approach_witch(traced, evidence, exchange=stage == 'witch-exchange', tarin=stage == 'tarin', tail_key=stage == 'tail-key', tail_cave=stage == 'tail-cave')
            if 'toadstool_acquired' not in env.journal.milestones or snapshot(env.pyboy)['health'] <= 0:
                raise RuntimeError('Missing physical living toadstool milestone')
            if stage == 'witch-exchange':
                current = snapshot(env.pyboy)
                if (current['toadstool'] or current['powder'] <= 0 or 12 not in current['inventory']
                        or current['dialog_state'] or 'powder_available' not in env.journal.milestones):
                    raise RuntimeError('Physical witch exchange did not finish with usable powder and closed dialogue')
            if stage == 'tarin':
                current = snapshot(env.pyboy)
                if current['tarin'] != 1 or current['dialog_state'] or 'raccoon_cured' not in env.journal.milestones:
                    raise RuntimeError('Tarin cure did not finish with a live latch and closed dialogue')
            if stage == 'tail-key':
                current = snapshot(env.pyboy)
                if not current['tail_key'] or current['dialog_state'] or 'tail_key_acquired' not in env.journal.milestones:
                    raise RuntimeError('Tail Key pickup did not finish with possession and closed dialogue')
            if stage == 'tail-cave':
                current = snapshot(env.pyboy)
                if (current['room'] != [1,0,0x17] or current['dialog_state']
                        or 'tail_cave_entered' not in env.journal.milestones):
                    raise RuntimeError('Missing settled living Tail Cave entry')
        except Exception as exc:
            status, failure = 'blocked', str(exc)
        finally:
            final = snapshot(env.pyboy)
            journal = env.journal.state()
            result = dict(status=status, failure=failure, steps=env.total_steps, frames=env.frames,
                damage_raw=env.journal.damage_raw, healing_raw=env.journal.healing_raw,
                final=final, milestones=env.journal.milestones, quest_success=bool(status == 'tail_cave_entered' and 'tail_cave_entered' in env.journal.milestones),
                exact_action_replay=False, assistance='scripted_known_route_with_source_grounded_rom_senses',
                human_interventions=0, optimizer_updates=0, reserved_evaluation_used=False)
            env.pyboy.screen.image.save(out/'final.png')
            with (out/'final.state').open('wb') as state_file:
                env.pyboy.save_state(state_file)
            env.close()
    write(out/'journal.json', journal)
    write(out/'skill-evidence.json', evidence)
    write(out/'result.json', result)
    replay = ProgressionEnv(out/'game.gbc', out/'initial.state', max_steps=12288, max_frames=300000)
    try:
        replay.reset(seed=0)
        for row in rows:
            returned = apply(replay, row['command'])
            if (fingerprint(replay) != row['fingerprint'] or replay.frames != row['frame']
                    or returned[4]['events'] != row['events'] or snapshot(replay.pyboy) != row['after']):
                raise AssertionError(f'Independent replay diverged at {row["decision"]}')
        if replay.journal.state() != journal:
            raise AssertionError('Independent journal differs')
        result['exact_action_replay'] = True
    finally:
        replay.close()
    result['wall_seconds'] = round(time.monotonic()-began, 3)
    write(out/'result.json', result)
    write(out/'manifest.json', dict(artifacts={p.name:file_hash(p) for p in out.iterdir()
        if p.is_file() and p.name != 'game.gbc'}))
    memory = WorldMemory.load(ROOT/'runs/progression-forest-progress-v1/memory-generation-4.json').next_generation()
    memory.import_verified_fixture(out)
    memory.verify_evidence()
    memory.save(out/'memory-generation-5.json')
    write(ROOT/'reports'/f'{out.name}.json', dict(result=result, evidence=evidence,
        output=str(out.relative_to(ROOT)), memory_version=memory.version))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--stage', choices=['toadstool', 'witch-approach', 'witch-exchange', 'tarin', 'tail-key', 'tail-cave'], default='toadstool')
    args = parser.parse_args()
    run(args.out.resolve(), args.stage)
