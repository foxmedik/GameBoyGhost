"""Bounded, frozen physical-variation collection; no optimizer or RAM perturbations."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import shutil
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from run_toadstool_progression import Trace, apply
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.transitions import BUTTONS
from gameboy_agent.world_memory import file_hash
from gameboy_agent.toadstool_teacher import execute as mushroom
from gameboy_agent.witch_approach import execute as quest

SOURCES = {'toadstool':'progression-forest-terrain-v5',
           'witch-approach':'progression-toadstool-v1',
           'witch-exchange':'progression-witch-approach-v4',
           'tarin':'progression-witch-exchange-v12',
           'tail-key':'progression-tarin-v3',
           'tail-cave':'progression-tail-key-v2',
           'house':'progression-tail-key-v2'}
MILESTONES = {'toadstool':'toadstool_acquired', 'witch-approach':None,
              'witch-exchange':'powder_available','tarin':'raccoon_cured',
              'tail-key':'tail_key_acquired','tail-cave':'tail_cave_entered',
              'house':'tail_cave_entered'}


def write(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n')
    temporary.replace(path)


def utc():
    return datetime.now(timezone.utc).isoformat()


def make_plan(seconds):
    cases = [dict(id='control-house',split='control',stage='house',idle=0,direction=None,move_frames=0)]
    # Disjoint physical startup configurations, specified before observing outcomes.
    for split,offset in (('development',0),('validation',1)):
        for i in range(20):
            cases.append(dict(id=f'{split}-house-{i:02d}',split=split,stage='house',
                              idle=2*i+offset+1,direction=(None,'left','right','up','down')[i%5],
                              move_frames=0 if i%5==0 else 1+i//5))
    # All remaining cases are development diagnostics, never promoted to validation.
    probes=[]
    rng=random.Random(20260911)
    for stage in SOURCES:
        if stage=='house': continue
        for i in range(120):
            probes.append(dict(id=f'probe-{stage}-{i:02d}',split='development_probe',stage=stage,
                              idle=i*4,direction=(None,'left','right','up','down')[i%5],
                              move_frames=0 if i%5==0 else 1+i//20))
    rng.shuffle(probes)
    cases.extend(probes)
    paths=[Path(__file__),ROOT/'scripts/run_toadstool_progression.py',
           *sorted((ROOT/'src/gameboy_agent').glob('*.py'))]
    focus=json.loads((ROOT/'configs/research_focus.json').read_text())
    return dict(schema='progression-longrun-v1',created_at=utc(),duration_seconds=seconds,
                scope='frozen_scripted_baseline_physical_variations',
                candidate='saved_house_to_key_commands_then_live_scripted_tail_cave_extension',
                distinction='House startup variation tests this mixed tape/script baseline. Stage probes test live suffix helpers after an exact physical house prefix; they are not full-quest reliability trials.',
                acceptance='At least 18/20 of the untouched house validation panel must complete alive with exact replay. No learning or generalization claim.',
                max_steps=12288,max_frames=300000,extension_decisions=2048,
                case_wall_seconds=180,minimum_free_disk_bytes=100*1024**3,minimum_available_memory_bytes=32*1024**3,
                stop_rules=['one hour admission deadline, then finish the current bounded case',
                            'source or policy hash change','3 consecutive infrastructure failures',
                            'fewer than 100 GiB free disk or 32 GiB available memory','STOP file present'],
                optimizer_updates=0,reserved_navigation_evaluation_used=False,
                cases=cases,source_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in paths},
                selected_policy=focus['selected_policy'],selected_policy_sha256=focus['selected_policy_sha256'])


def freeze(out,seconds):
    out.mkdir(parents=True,exist_ok=False)
    for source in set(SOURCES.values()):
        directory=ROOT/'runs'/source
        for name,digest in json.loads((directory/'manifest.json').read_text())['artifacts'].items():
            if file_hash(directory/name)!=digest: raise ValueError(f'Source artifact mismatch: {source}/{name}')
    plan=make_plan(seconds)
    plan['prefix_hashes']={stage:file_hash(ROOT/'runs'/name/'trajectory.jsonl') for stage,name in SOURCES.items()}
    for name in ('game.gbc','initial.state'):
        shutil.copy2(ROOT/'runs/progression-tail-key-v2'/name,out/name)
    plan['rom_sha256']=file_hash(out/'game.gbc')
    plan['initial_state_sha256']=file_hash(out/'initial.state')
    write(out/'plan.json',plan)
    for name in plan['source_hashes']:
        dest=out/'source-snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,dest)
    return plan


def check_source(plan):
    for name,digest in plan['source_hashes'].items():
        if file_hash(ROOT/name)!=digest: raise ValueError(f'Frozen source changed: {name}')
    if file_hash(ROOT/plan['selected_policy'])!=plan['selected_policy_sha256']:
        raise ValueError('Selected model changed')


def perturb(env,spec):
    if spec['idle']:
        env.step_input_events(release=BUTTONS,frames=spec['idle'])
    if spec['direction']:
        key=spec['direction']
        env.step_input_events([key],release=[b for b in BUTTONS if b!=key],
                              frames=spec['move_frames'],release_after=[key])
        env.step_input_events(frames=1)


class TimedTrace(Trace):
    def __init__(self,*args,deadline,**kwargs):
        super().__init__(*args,**kwargs)
        self.deadline=deadline
    def record(self,*args,**kwargs):
        if time.monotonic()>self.deadline: raise TimeoutError('Case wall-time limit')
        return super().record(*args,**kwargs)


def collect_case(out,spec,plan):
    directory=out/'cases'/spec['id'];directory.mkdir(parents=True,exist_ok=False)
    began=time.monotonic();rows=[];evidence=[]
    env=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=plan['max_steps'],max_frames=plan['max_frames'])
    source=ROOT/'runs'/SOURCES[spec['stage']]
    phase='setup';failure=None;success=False;replay_ok=False;infrastructure_failure=False
    with (directory/'trajectory.jsonl').open('x') as stream:
        traced=TimedTrace(env,stream,rows,deadline=began+plan['case_wall_seconds'])
        try:
            env.reset(seed=0)
            if spec['stage']=='house': perturb(traced,spec)
            phase='prefix'
            prefix_path=source/'trajectory.jsonl'
            if file_hash(prefix_path)!=plan['prefix_hashes'][spec['stage']]:
                infrastructure_failure=True
                raise ValueError('Frozen prefix trace changed')
            for line in prefix_path.open():
                old=json.loads(line);apply(traced,old['command'])
                if spec['stage']!='house' or spec['id']=='control-house':
                    if rows[-1]['fingerprint']!=old['fingerprint']:
                        infrastructure_failure=True
                        raise AssertionError('Exact setup prefix diverged')
            phase='perturbation'
            if spec['stage']!='house': perturb(traced,spec)
            evidence.append(dict(kind='suffix_start',frame=env.frames,state=snapshot(env.pyboy)))
            phase='live_suffix';traced.decision_limit=env.total_steps+plan['extension_decisions']
            stage=spec['stage']
            if stage=='toadstool': mushroom(traced,evidence)
            else: quest(traced,evidence,exchange=stage=='witch-exchange',tarin=stage=='tarin',
                        tail_key=stage=='tail-key',tail_cave=stage in ('tail-cave','house'))
            final=snapshot(env.pyboy)
            if stage=='witch-approach':
                success=final['room']==[0,0,0x62] and bool(final['toadstool'])
            else: success=MILESTONES[stage] in env.journal.milestones
            success=bool(success and final['health']>0 and not final['dialog_state'])
            if not success: failure='Requested live milestone did not satisfy final-state criterion'
        except Exception as exc:
            failure=f'{type(exc).__name__}: {exc}'
        finally:
            final=snapshot(env.pyboy);journal=env.journal.state()
            env.pyboy.screen.image.save(directory/'final.png')
            with (directory/'final.state').open('wb') as f: env.pyboy.save_state(f)
            env.close()
    phase_failed=phase if failure else None
    write(directory/'journal.json',journal);write(directory/'evidence.json',evidence)
    replay=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=plan['max_steps'],max_frames=plan['max_frames'])
    try:
        replay.reset(seed=0)
        for row in rows:
            if time.monotonic()>began+plan['case_wall_seconds']:
                raise TimeoutError('Case replay wall-time limit')
            value=apply(replay,row['command'])
            if (fingerprint(replay)!=row['fingerprint'] or snapshot(replay.pyboy)!=row['after']
                    or replay.frames!=row['frame'] or value[4]['events']!=row['events']):
                raise AssertionError(f'Replay divergence at {row["decision"]}')
        if replay.journal.state()!=journal: raise AssertionError('Journal replay mismatch')
        replay_ok=True
    except Exception as exc:
        infrastructure_failure=True;failure=f'{failure or ""}; Replay: {exc}'
    finally: replay.close()
    result=dict(spec=spec,success=success and replay_ok,failure=failure,phase_failed=phase_failed,
                infrastructure_failure=infrastructure_failure,exact_replay=replay_ok,
                steps=len(rows),frames=rows[-1]['frame'] if rows else 0,
                damage_raw=journal['damage_raw'],healing_raw=journal['healing_raw'],final=final,
                milestones=journal['milestones'],wall_seconds=round(time.monotonic()-began,3),
                optimizer_updates=0,human_interventions=0)
    write(directory/'result.json',result)
    write(directory/'manifest.json',dict(artifacts={p.name:file_hash(p) for p in directory.iterdir() if p.is_file()}))
    return result


def summarize(out,plan,results,started,status,reason=None):
    groups={}
    for r in results:
        key=f'{r["spec"]["split"]}/{r["spec"]["stage"]}'
        g=groups.setdefault(key,dict(cases=0,successes=0,exact_replays=0,deaths=0))
        g['cases']+=1;g['successes']+=int(r['success']);g['exact_replays']+=int(r['exact_replay']);g['deaths']+=int(r['final']['health']==0)
    validation=[r for r in results if r['spec']['split']=='validation']
    summary=dict(status=status,reason=reason,updated_at=utc(),started_at=started,
                 completed_cases=len(results),planned_cases=len(plan['cases']),groups=groups,
                 total_recorded_decisions=sum(r['steps'] for r in results),
                 total_recorded_frames=sum(r['frames'] for r in results),
                 replay_decisions=sum(r['steps'] for r in results if r['exact_replay']),
                 validation_complete=len(validation)==20,
                 validation_passed=len(validation)==20 and sum(r['success'] for r in validation)>=18,
                 failures=dict(Counter(f'{r["spec"]["stage"]}: {r["failure"]}' for r in results if r['failure'])),
                 optimizer_updates=0,reserved_navigation_evaluation_used=False,
                 scope=plan['scope'],results_file=str(out/'results.jsonl'))
    write(out/'summary.json',summary)
    write(ROOT/'reports'/f'{out.name}.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=3600)
    parser.add_argument('--max-cases',type=int)
    args=parser.parse_args();out=args.out.resolve()
    if not 1<=args.seconds<=3600: parser.error('seconds must be 1..3600')
    plan=freeze(out,args.seconds);check_source(plan)
    started=utc();deadline=time.monotonic()+args.seconds;results=[];consecutive_errors=0;reason='all planned cases completed'
    write(out/'process.json',dict(pid=os.getpid(),started_at=started,admission_seconds=args.seconds))
    summarize(out,plan,results,started,'running')
    with (out/'results.jsonl').open('x') as stream:
        for spec in plan['cases']:
            if time.monotonic()>=deadline: reason='one-hour admission deadline reached';break
            if args.max_cases and len(results)>=args.max_cases: reason='requested case cap';break
            if (out/'STOP').exists(): reason='STOP requested';break
            if shutil.disk_usage(out).free<plan['minimum_free_disk_bytes']: reason='disk floor';break
            if psutil.virtual_memory().available<plan['minimum_available_memory_bytes']: reason='memory floor';break
            try: check_source(plan)
            except Exception as exc: reason=str(exc);break
            try: result=collect_case(out,spec,plan)
            except Exception as exc:
                reason=f'Infrastructure exception: {type(exc).__name__}: {exc}'
                write(out/'fatal.json',dict(error=reason,spec=spec));break
            results.append(result);stream.write(json.dumps(result)+'\n');stream.flush()
            consecutive_errors=consecutive_errors+1 if result['infrastructure_failure'] else 0
            summarize(out,plan,results,started,'running')
            print(json.dumps(dict(case=spec['id'],success=result['success'],replay=result['exact_replay'],seconds=result['wall_seconds'])),flush=True)
            if spec['id']=='control-house' and not result['success']:
                reason='baseline control failed';break
            if consecutive_errors>=3: reason='three consecutive infrastructure failures';break
    try: check_source(plan)
    except Exception as exc: reason=f'Final source verification failed: {exc}'
    summary=summarize(out,plan,results,started,'finished',reason)
    write(out/'completion.json',dict(completed_at=utc(),summary=summary))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__': main()
