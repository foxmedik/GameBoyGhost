"""Collect teacher recoveries from frozen student-created room-15 stalls."""
import argparse, json, shutil, sys, time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.tail_cave_progression import clear_compass_room
from gameboy_agent.world_memory import file_hash
from collect_room15_overnight import prefix, senses
from run_toadstool_progression import Trace, apply


def write(path,value):
    temporary=path.with_suffix('.tmp'); temporary.write_text(json.dumps(value,indent=2)+'\n'); temporary.replace(path)


def normalized(value): return json.loads(json.dumps(value))


def run_case(root,spec,plan):
    student_root=ROOT/plan['student_gate']; student=student_root/spec['student_case']; source=ROOT/plan['source']/f"development-house-{spec['base']:02d}"; out=root/spec['id'];out.mkdir(exist_ok=False)
    for name in ('game.gbc','initial.state'):shutil.copy2(source/name,out/name)
    commands=[json.loads(line) for line in (student/'trajectory.jsonl').read_text().splitlines()]
    manifest=json.loads((student/'manifest.json').read_text())
    for name,digest in manifest.items():
        if file_hash(student/name)!=digest:raise RuntimeError(f'Student artifact changed: {student/name}')
    def make():return ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=16000,max_frames=300000,completion_milestone=None)
    env=make(); rows=[]; evidence=[];failure=None;started=time.monotonic()
    try:
        env.reset(seed=0);prefix(env,source)
        env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['idle'])
        for row in commands:
            info=apply(env,row['command'])[4]
            if fingerprint(env)!=row['fingerprint'] or normalized(snapshot(env.pyboy))!=normalized(row['after']) or env.frames!=row['frame'] or info['events']!=row['events']:raise RuntimeError(f'Student trace mismatch at {row["decision"]}')
        recovery_start=senses(env); start_damage=env.journal.damage_raw
        with (out/'trajectory.jsonl').open('x') as stream:
            traced=Trace(env,stream,rows); clear_compass_room(traced,evidence)
        final=senses(env); damage=env.journal.damage_raw-start_damage
    except Exception as exc:
        failure=f'{type(exc).__name__}: {exc}'; final=senses(env);damage=0 if 'start_damage' not in locals() else env.journal.damage_raw-start_damage
    finally:
        journal=deepcopy(env.journal.state());env.pyboy.screen.image.save(out/'final.png');env.close()
    replay=make()
    try:
        replay.reset(seed=0);prefix(replay,source);replay.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['idle'])
        for row in commands+rows:
            info=apply(replay,row['command'])[4]
            assert fingerprint(replay)==row['fingerprint'] and normalized(snapshot(replay.pyboy))==normalized(row['after']) and replay.frames==row['frame'] and info['events']==row['events']
        assert replay.journal.state()==journal
    finally:replay.close()
    result=dict(spec=spec,success=failure is None,failure=failure,recovery_start=recovery_start,final=final,damage_raw=damage,exact_replay=True,teacher_commands=len(rows),control='teacher_correction_after_student_stall',training_eligible=failure is None,seconds=round(time.monotonic()-started,2));write(out/'evidence.json',evidence);write(out/'result.json',result);write(out/'manifest.json',{p.name:file_hash(p) for p in out.iterdir() if p.is_file()});return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();plan=json.loads(args.plan.read_text())
    for name,digest in plan['frozen_inputs'].items():
        if file_hash(ROOT/name)!=digest:raise RuntimeError(f'Frozen input changed: {name}')
    args.out.mkdir(exist_ok=False);shutil.copy2(args.plan,args.out/'plan.json');results=[]
    for spec in plan['cases']:
        results.append(run_case(args.out,spec,plan));write(args.out/'summary.json',dict(status='running',cases=len(results),planned=len(plan['cases']),successes=sum(r['success'] for r in results),exact_replays=sum(r['exact_replay'] for r in results),training_started=False,validation_loaded=False,results=results))
    summary=json.loads((args.out/'summary.json').read_text());summary['status']='complete';write(args.out/'summary.json',summary)


if __name__=='__main__':main()
