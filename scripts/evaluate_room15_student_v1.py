"""Continuous autonomous room-15 gate; the teacher only enters the room."""
import argparse, json, shutil, sys, time
from copy import deepcopy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
import torch
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.room15_model import action_command, feature
from gameboy_agent.tail_cave_progression import GEL, enter_compass_room
from gameboy_agent.tail_cave_teacher import entities
from gameboy_agent.world_memory import file_hash
from collect_room15_overnight import prefix, senses
from run_toadstool_progression import Trace, apply
from train_room15_student_v1 import Room15Net


def write(path, value):
    temporary = path.with_suffix('.tmp'); temporary.write_text(json.dumps(value, indent=2) + '\n'); temporary.replace(path)


def run_case(root, spec, plan):
    source = ROOT / plan['source'] / f"development-house-{spec['base']:02d}"; out = root / spec['id']; out.mkdir(exist_ok=False)
    for name in ('game.gbc', 'initial.state'): shutil.copy2(source / name, out / name)
    saved = torch.load(ROOT / plan['candidate'], map_location='cpu'); model = Room15Net(saved['inputs'], saved['outputs']); model.load_state_dict(saved['model']); model.eval()
    def make(): return ProgressionEnv(out / 'game.gbc', out / 'initial.state', max_steps=16000, max_frames=300000, completion_milestone=None)
    env, rows, evidence, history, failure = make(), [], [], [], None; started = time.monotonic()
    try:
        env.reset(seed=0); prefix(env, source)
        if spec['idle']: env.step_input_events(release=('up','down','left','right','a','b','start','select'), frames=spec['idle'])
        traced = Trace(env, (out / 'trajectory.jsonl').open('x'), rows)
        enter_compass_room(traced, evidence); initial = senses(env); start_damage = env.journal.damage_raw
        for decision in range(plan['decision_budget']):
            state = snapshot(env.pyboy)
            if state['room'] != [1,0,0x15] or not state['health']: raise RuntimeError(f'Student left living room-15 contract: {state["room"]}')
            if not entities(env, GEL): break
            observation = senses(env); x = torch.from_numpy((feature(observation, history) - saved['mean']) / saved['scale'])
            with torch.no_grad(): action = int(model(x).argmax())
            buttons, frames = action_command(action); traced.step_buttons(buttons, action_frames=frames); history.append(action)
        else: raise RuntimeError(f'Student exhausted {plan["decision_budget"]}-decision room15 budget')
        final = senses(env); damage = env.journal.damage_raw - start_damage
        if final['state']['room'] != [1,0,0x15] or not final['state']['health'] or entities(env, GEL): raise RuntimeError('Student room15 completion contract failed')
    except Exception as exc:
        failure = f'{type(exc).__name__}: {exc}'; final = senses(env); damage = 0 if 'start_damage' not in locals() else env.journal.damage_raw - start_damage
    finally:
        journal = deepcopy(env.journal.state()); env.pyboy.screen.image.save(out / 'final.png'); env.close()
    replay = make()
    try:
        replay.reset(seed=0); prefix(replay, source)
        if spec['idle']:
            replay.step_input_events(release=('up','down','left','right','a','b','start','select'), frames=spec['idle'])
        for row in rows:
            info = apply(replay, row['command'])[4]
            assert fingerprint(replay) == row['fingerprint'] and replay.frames == row['frame'] and info['events'] == row['events']
            # In-memory Trace rows retain tuples; compare both sides in the
            # JSON representation that is persisted as the replay artifact.
            assert json.loads(json.dumps(snapshot(replay.pyboy))) == json.loads(json.dumps(row['after']))
        assert replay.journal.state() == journal
    finally: replay.close()
    result = dict(spec=spec, success=failure is None, failure=failure, initial=initial, final=final, damage_raw=damage, exact_replay=True, student_decisions=len(history), control='student_only_room15', teacher_action_fraction=0.0, autonomous_room15_evaluated=True, seconds=round(time.monotonic()-started,2))
    write(out / 'evidence.json', evidence); write(out / 'result.json', result); write(out / 'manifest.json', {p.name:file_hash(p) for p in out.iterdir() if p.is_file()}); return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--plan', type=Path, required=True); parser.add_argument('--out', type=Path, required=True); args = parser.parse_args(); plan=json.loads(args.plan.read_text())
    for path, key in ((Path(__file__),'evaluator_sha256'),(ROOT / plan['candidate'],'candidate_sha256'),(ROOT / plan['experiment'],'experiment_sha256')):
        if file_hash(path) != plan[key]: raise RuntimeError(f'Frozen input changed: {path}')
    if 'cases_from' in plan:
        cases_path = ROOT / plan['cases_from']
        if file_hash(cases_path) != plan['cases_source_sha256']: raise RuntimeError('Frozen case source changed')
        cases = json.loads(cases_path.read_text())['cases']
    else:
        cases = plan['cases']
    args.out.mkdir(exist_ok=False); shutil.copy2(args.plan, args.out / 'plan.json'); results=[]
    # Run in this process: process-spawned PyBoy instances have exhibited
    # nonterminating replay work on this host.
    for spec in cases:
        results.append(run_case(args.out, spec, plan))
        write(args.out / 'summary.json', dict(status='running',cases=len(results),planned=len(cases),successes=sum(r['success'] for r in results),exact_replays=sum(r['exact_replay'] for r in results),validation_loaded=False,results=sorted(results,key=lambda r:r['spec']['id'])))
    summary=json.loads((args.out/'summary.json').read_text()); low=[r for r in results if r['initial']['state']['health'] <= 4]
    summary.update(status='complete',required_successes=plan['required_successes'],half_heart_cases=len(low),half_heart_successes=sum(r['success'] for r in low),gate_passed=sum(r['success'] for r in results)>=plan['required_successes'] and sum(r['success'] for r in low)>=plan['required_half_heart_successes'])
    write(args.out / 'summary.json', summary)


if __name__ == '__main__': main()
