"""Export fresh zero-damage demonstrations only after a frozen teacher gate passes."""
import argparse
import json
from pathlib import Path
from hashlib import sha256


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--collection', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads((args.collection / 'plan.json').read_text())
    if plan['schema'] != 'room15-teacher-demonstrations-v1' or not plan['labels_authorized']:
        raise RuntimeError('Only a fresh, explicitly authorized demonstration collection may supply labels')
    gate_path = Path(plan['teacher_gate_summary'])
    if digest(gate_path) != plan['teacher_gate_sha256']:
        raise RuntimeError('Teacher gate evidence changed')
    gate = json.loads(gate_path.read_text())
    if gate['status'] != 'complete' or not gate['gate_passed']:
        raise RuntimeError('Teacher gate has not passed')
    gate_plan = json.loads((gate_path.parent / 'plan.json').read_text())
    for name, expected in plan['frozen_inputs'].items():
        if digest(Path(name)) != expected:
            raise RuntimeError(f'Collection input changed: {name}')
        if name.startswith('src/') and gate_plan['frozen_inputs'].get(name) != expected:
            raise RuntimeError(f'Teacher changed since acceptance: {name}')
    summary = json.loads((args.collection / 'summary.json').read_text())
    if summary['status'] != 'complete':
        raise RuntimeError('Collection is incomplete')
    args.output.mkdir(exist_ok=False)
    included, excluded, count = [], [], 0
    with (args.output / 'labels.jsonl').open('x') as output:
        for result in summary['results']:
            case_id = result['spec']['id']
            if not (result['success'] and result['exact_replay'] and result['damage_raw'] == 0):
                excluded.append(case_id)
                continue
            case = args.collection / case_id
            manifest = json.loads((case / 'manifest.json').read_text())
            for name, expected in manifest.items():
                if digest(case / name) != expected:
                    raise RuntimeError(f'Case artifact changed: {case_id}/{name}')
            observations = [json.loads(line) for line in (case / 'observations.jsonl').read_text().splitlines()]
            actions = [json.loads(line) for line in (case / 'trajectory.jsonl').read_text().splitlines()]
            if len(observations) != len(actions) + 1:
                raise RuntimeError(f'Observation/action alignment failed: {case_id}')
            for index, (observation, action) in enumerate(zip(observations, actions)):
                if observation['state']['room'] != [1, 0, 0x15]:
                    continue
                output.write(json.dumps(dict(case_id=case_id, command_index=index,
                    observation=observation, command=action['command'],
                    source_trajectory_sha256=manifest['trajectory.jsonl'],
                    control='teacher_demonstration', on_policy_correction=False)) + '\n')
                count += 1
            included.append(case_id)
    report = dict(schema='room15-teacher-labels-v1', collection=str(args.collection),
                  teacher_gate=str(gate_path), included_cases=included, excluded_cases=excluded,
                  labels=count, labels_sha256=digest(args.output / 'labels.jsonl'),
                  policy='Fresh zero-damage exact-replay successes only; no diagnostic or gate trajectories',
                  on_policy_corrections=False, training_started=False, validation_loaded=False)
    (args.output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
