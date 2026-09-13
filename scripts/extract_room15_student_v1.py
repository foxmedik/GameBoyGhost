"""Freeze clean teacher demonstrations into train/development arrays."""
import argparse, json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
from gameboy_agent.room15_model import action_index, feature
from gameboy_agent.world_memory import file_hash


def write(path, value): path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--plan', type=Path, required=True); parser.add_argument('--out', type=Path, required=True); args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if file_hash(Path(__file__)) != plan['extractor_sha256']: raise RuntimeError('Frozen extractor changed')
    manifest_path = ROOT / plan['labels_manifest']
    if file_hash(manifest_path) != plan['labels_manifest_sha256']: raise RuntimeError('Frozen label manifest changed')
    manifest = json.loads(manifest_path.read_text())
    if manifest['training_started'] or manifest['validation_loaded']: raise RuntimeError('Label source violates experiment boundary')
    included = set(manifest['included_cases']); splits = {'train': set(plan['train_cases']), 'development': set(plan['development_cases'])}
    if splits['train'] | splits['development'] != included or splits['train'] & splits['development']: raise RuntimeError('Split must partition all approved clean cases')
    rows = [json.loads(line) for line in (manifest_path.parent / 'labels.jsonl').read_text().splitlines()]
    result = {}
    for split, cases in splits.items():
        x, y, provenance, histories = [], [], [], {}
        for row in rows:
            case = row['case_id']
            if case not in cases: continue
            command = row['command']; action = action_index(command)
            if action is None: continue
            history = histories.setdefault(case, [])
            x.append(feature(row['observation'], history)); y.append(action); provenance.append([case, row['command_index']]); history.append(action)
        result[split] = (np.stack(x), np.asarray(y, dtype=np.int64), np.asarray(provenance))
    args.out.mkdir(parents=True, exist_ok=False); shutil.copy2(args.plan, args.out / 'plan.json')
    output = {'schema': 'room15-student-data-v1', 'experiment_sha256': file_hash(args.plan), 'validation_loaded': False, 'splits': {}}
    for split, (x, y, provenance) in result.items():
        path = args.out / f'{split}.npz'; np.savez_compressed(path, x=x, y=y, provenance=provenance)
        output['splits'][split] = {'cases': sorted(splits[split]), 'rows': len(x), 'sha256': file_hash(path)}
    write(args.out / 'manifest.json', output); print(json.dumps(output, indent=2))


if __name__ == '__main__': main()
