"""Thirty-minute, guided-recovery diagnostic batch; never an autonomous gate."""
import argparse, json, shutil, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT / 'scripts')]
from evaluate_room15_student_v5_guided import run_case, write
from gameboy_agent.world_memory import file_hash


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True); parser.add_argument('--minutes', type=float, default=30); args = parser.parse_args()
    plan = {'source': 'runs/state-driven-tail-cave-disengage-guarded-v1', 'candidate': 'runs/room15-student-v4-candidate/candidate.pt', 'decision_budget': 700,
            'control': 'Guided diagnostic only: V4 acts except at a state-checked early y80 recovery trigger.', 'autonomous_room15_evaluated': False,
            'training_started': False, 'validation_loaded': False, 'duration_minutes': args.minutes}
    args.out.mkdir(parents=True, exist_ok=False); write(args.out / 'plan.json', plan)
    started = time.monotonic(); results = []; index = 0
    while time.monotonic() - started < args.minutes * 60:
        spec = {'id': f'guided-v5-{index:03d}', 'base': index % 20, 'idle': 200 + index}
        results.append(run_case(args.out, spec, plan)); index += 1
        write(args.out / 'summary.json', {'status': 'running', 'cases': len(results), 'successes': sum(r['success'] for r in results),
            'exact_replays': sum(r['exact_replay'] for r in results), 'guided_interventions': sum(r['guided_interventions'] for r in results),
            'autonomous_room15_evaluated': False, 'training_started': False, 'validation_loaded': False, 'results': results})
    summary = json.loads((args.out / 'summary.json').read_text()); summary['status'] = 'complete'; summary['elapsed_seconds'] = round(time.monotonic() - started, 2); write(args.out / 'summary.json', summary)


if __name__ == '__main__': main()
