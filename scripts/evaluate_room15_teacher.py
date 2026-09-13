"""Frozen continuous teacher gate; produces no training labels."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path

from collect_room15_overnight import ROOT, run_case, write
from gameboy_agent.world_memory import file_hash


def verify(plan):
    for name, digest in plan['frozen_inputs'].items():
        if file_hash(ROOT / name) != digest:
            raise RuntimeError(f'Frozen gate input changed: {name}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    verify(plan)
    out = ROOT / plan['output']
    out.mkdir(exist_ok=False)
    write(out / 'plan.json', plan)
    results = []
    try:
        with ProcessPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(run_case, out, spec, plan) for spec in plan['cases']]
            for future in as_completed(futures):
                results.append(future.result())
                verify(plan)
                summary = dict(status='running', cases=len(results), planned=len(plan['cases']),
                               successes=sum(r['success'] for r in results),
                               exact_replays=sum(r['exact_replay'] for r in results),
                               zero_damage_successes=sum(r['success'] and r['damage_raw'] == 0 for r in results),
                               validation_loaded=False, training_started=False,
                               results=sorted(results, key=lambda r: r['spec']['id']))
                write(out / 'summary.json', summary)
        low = [r for r in results if r['initial']['state']['health'] <= 4]
        summary['half_heart_cases'] = len(low)
        summary['half_heart_zero_damage_successes'] = sum(r['success'] and r['damage_raw'] == 0 for r in low)
        summary['gate_passed'] = (len(results) == plan['required_successes']
                                  and all(r['success'] and r['exact_replay'] for r in results)
                                  and len(low) == plan['required_half_heart_zero_damage']
                                  and all(r['success'] and r['damage_raw'] == 0 for r in low))
        summary['status'] = 'complete'
        write(out / 'summary.json', summary)
    except BaseException as exc:
        write(out / 'failure.json', dict(error=f'{type(exc).__name__}: {exc}', completed=len(results)))
        raise


if __name__ == '__main__':
    main()
