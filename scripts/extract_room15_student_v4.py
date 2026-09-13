"""Build a lightly mixed, sustained-block recovery dataset for room-15 v4."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
import numpy as np

from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.room15_model_v4 import action_index, temporal_feature, update
from gameboy_agent.world_memory import file_hash
from collect_room15_overnight import prefix, senses
from run_toadstool_progression import apply


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def clean_rows(labels, cases):
    result = []
    for case in cases:
        rows = sorted((row for row in labels if row['case_id'] == case), key=lambda row: row['command_index'])
        history = []
        for index, row in enumerate(rows):
            action = action_index(row['command'])
            if action is None: continue
            result.append((temporal_feature(row['observation'], history), action, [case, row['command_index']]))
            after = rows[index + 1]['observation']['state'] if index + 1 < len(rows) else row['observation']['state']
            history = update(history, action, row['observation']['state'], after)
    return result


def normalized(value): return json.loads(json.dumps(value))


def escape_rows(plan):
    root = ROOT / plan['escapes']
    summary = json.loads((root / 'summary.json').read_text())
    if summary['successes'] != len(plan['escape_limits']) or summary['exact_replays'] != len(plan['escape_limits']):
        raise RuntimeError('Escape collection did not fully pass exact replay')
    result = []
    for item in summary['results']:
        case_id = item['spec']['id']
        limit = plan['escape_limits'][case_id]
        if not item['success'] or not item['training_eligible']:
            raise RuntimeError(f'Unverified escape: {case_id}')
        spec = item['spec']
        source = ROOT / plan['source'] / f"development-house-{spec['base']:02d}"
        student = ROOT / plan['student_gate'] / spec['student_case']
        teacher = root / case_id
        student_rows = [json.loads(line) for line in (student / 'trajectory.jsonl').read_text().splitlines()][:spec['blocked_index'] + 1]
        teacher_rows = [json.loads(line) for line in (teacher / 'trajectory.jsonl').read_text().splitlines()][:limit]
        env = ProgressionEnv(source / 'game.gbc', source / 'initial.state', max_steps=16000,
                             max_frames=300000, completion_milestone=None)
        history = []
        try:
            env.reset(seed=0); prefix(env, source)
            env.step_input_events(release=('up','down','left','right','a','b','start','select'), frames=spec['idle'])
            for row in student_rows:
                before = normalized(snapshot(env.pyboy)); action = action_index(row['command'])
                info = apply(env, row['command'])[4]; after = normalized(snapshot(env.pyboy))
                if fingerprint(env) != row['fingerprint'] or after != normalized(row['after']) or env.frames != row['frame'] or info['events'] != row['events']:
                    raise RuntimeError(f'Student prefix replay mismatch: {case_id}')
                if action is not None: history = update(history, action, before, after)
            for decision, row in enumerate(teacher_rows):
                before = normalized(snapshot(env.pyboy)); action = action_index(row['command'])
                if action is None:
                    raise RuntimeError(f'Unsupported action inside bounded escape span: {case_id}/{decision}')
                result.append((temporal_feature(senses(env), history), action, [case_id, decision], plan['recovery_loss_weight']))
                info = apply(env, row['command'])[4]; after = normalized(snapshot(env.pyboy))
                if fingerprint(env) != row['fingerprint'] or after != normalized(row['after']) or env.frames != row['frame'] or info['events'] != row['events']:
                    raise RuntimeError(f'Teacher escape replay mismatch: {case_id}/{decision}')
                history = update(history, action, before, after)
        finally:
            env.close()
    return result


def save_split(out, name, rows):
    x = np.stack([row[0] for row in rows]); y = np.asarray([row[1] for row in rows], dtype=np.int64)
    provenance = np.asarray([row[2] for row in rows]); weight = np.asarray([row[3] for row in rows], dtype=np.float32)
    path = out / f'{name}.npz'; np.savez_compressed(path, x=x, y=y, provenance=provenance, weight=weight)
    return {'rows': len(rows), 'recovery_rows': int((weight < 1).sum()), 'sha256': file_hash(path)}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--plan', type=Path, required=True); parser.add_argument('--out', type=Path, required=True); args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    for path, expected in plan['frozen_inputs'].items():
        if file_hash(ROOT / path) != expected: raise RuntimeError(f'Frozen input changed: {path}')
    labels_manifest = ROOT / plan['labels_manifest']; manifest = json.loads(labels_manifest.read_text())
    if manifest['validation_loaded']: raise RuntimeError('Label manifest loaded validation')
    labels = [json.loads(line) for line in (labels_manifest.parent / 'labels.jsonl').read_text().splitlines()]
    train = [(x, y, p, 1.0) for x, y, p in clean_rows(labels, plan['train_cases'])] + escape_rows(plan)
    development = [(x, y, p, 1.0) for x, y, p in clean_rows(labels, plan['development_cases'])]
    args.out.mkdir(parents=True, exist_ok=False); shutil.copy2(args.plan, args.out / 'plan.json')
    report = {'schema': 'room15-student-data-v4-targeted-escape', 'experiment_sha256': file_hash(args.plan),
              'validation_loaded': False, 'splits': {'train': save_split(args.out, 'train', train), 'development': save_split(args.out, 'development', development)}}
    write(args.out / 'manifest.json', report); print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
