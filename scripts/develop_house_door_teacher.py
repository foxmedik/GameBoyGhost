"""One frozen fresh-house development probe with mandatory independent replay."""
import argparse
from collections import deque
import traceback
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from house_door_teacher import execute,MODELS
from run_toadstool_progression import Trace,apply,write
from collect_room15_overnight import senses,normalized
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.world_memory import file_hash
from gameboy_agent.battle_ready_endpoint import require_battle_ready

p=argparse.ArgumentParser()
p.add_argument('--output',required=True)
p.add_argument('--idle',type=int,default=23)
p.add_argument('--recovery',action='store_true')
p.add_argument('--qualification-binding')
p.add_argument('--binding-sha256')
p.add_argument('--case-id')
p.add_argument('--hypothesis',default='Assemble existing guided stages from one fresh house start')
a=p.parse_args()
out=ROOT/a.output;out.mkdir(parents=True,exist_ok=False)
start=dict(rom='runs/state-driven-tail-cave-disengage-guarded-v1/development-house-00/game.gbc',
           initial_state='runs/state-driven-tail-cave-disengage-guarded-v1/development-house-00/initial.state')
paths=sorted((ROOT/'src/gameboy_agent').glob('*.py'))+sorted((ROOT/'scripts').glob('*.py'))
paths+=sorted((ROOT/'configs').glob('*.json'))
paths += [ROOT/v for v in MODELS.values()]
for config in ('sword_controller.json','navigation_experiment.json'):
    value=json.loads((ROOT/'configs'/config).read_text())
    if value.get('policy_path'):paths.append(ROOT/value['policy_path'])
binding={str(v.relative_to(ROOT)):file_hash(v) for v in paths}
start_hashes={v:file_hash(ROOT/v) for v in start.values()}
qualification=bool(a.qualification_binding)
if qualification:
    candidate_path=ROOT/a.qualification_binding
    if file_hash(candidate_path)!=a.binding_sha256:raise RuntimeError('Candidate binding hash mismatch')
    candidate=json.loads(candidate_path.read_text())
    if candidate['binding']!=binding or candidate['start_hashes']!=start_hashes:
        raise RuntimeError('Frozen candidate source/model/start binding mismatch')
    panel_path=ROOT/candidate['panel']
    if file_hash(panel_path)!=candidate['panel_sha256']:raise RuntimeError('Frozen panel changed')
    panel=json.loads(panel_path.read_text())
    case=next(c for c in panel['cases'] if c['id']==a.case_id)
    if (case['start']!=start or case['seed']!=0 or case['house_idle_frames']!=a.idle
            or (case['kind']=='recovery')!=a.recovery or case['max_decisions']!=30000
            or case['max_emulator_frames']!=150000 or case['max_wall_seconds']!=900):
        raise RuntimeError('Case parameters differ from frozen panel')
elif a.case_id or a.binding_sha256:
    raise RuntimeError('Qualification metadata without binding')
write(out/'plan.json',dict(schema='fresh-house-door-development-probe-v1',idle_frames=a.idle,
     max_decisions=30000,max_frames=150000,max_wall_seconds=900,start=start,hypothesis=a.hypothesis,
     start_hashes=start_hashes,binding=binding,recovery=a.recovery,qualification=qualification,case_id=a.case_id,training_eligible=False,
     forbidden_room=[1,0,6],success='Full-health settled open boss door outside; exact full replay'))
def make():return ProgressionEnv(ROOT/start['rom'],ROOT/start['initial_state'],
    max_steps=30000,max_frames=150000,completion_milestone=None)
base=make();base.reset(seed=0)
rows=[];evidence=[];failure=None;began=time.monotonic()
challenge={'first_arrival':None}
recent_observations=deque(maxlen=240)
failure_traceback=None
with (out/'trajectory.jsonl').open('x') as f:
    env=Trace(base,f,rows);env.decision_limit=30000
    original=env.record
    def record(method,*args,**kwargs):
        if time.monotonic()-began>=900:raise RuntimeError('Frozen development wall budget exhausted')
        result=original(method,*args,**kwargs)
        state=snapshot(base.pyboy)
        m=base.pyboy.memory
        recent_observations.append(dict(decision=len(rows)-1,frame=env.frames,state=state,
            command=rows[-1]['command'],entities=senses(base)['entities'],
            ram={hex(v):int(m[v]) for v in (0xFF9E,0xFFA2,0xC11C,0xC137,0xDB93,0xDB94)}))
        if state['room']==[1,0,6]:raise RuntimeError('Forbidden boss-room entry')
        if state['room']==[1,0,29] and challenge['first_arrival'] is None:
            m=base.pyboy.memory
            challenge['first_arrival']=dict(state=state,frame=env.frames,pending_damage=int(m[0xDB94]),pending_healing=int(m[0xDB93]))
            if a.recovery and not (state['health']==4 and 68<=state['x']<=76
                    and 114<=state['y']<=128 and not m[0xDB94] and not m[0xDB93]
                    and 10 not in state['inventory']):
                raise RuntimeError('Actual half-heart first-arrival prerequisite failed')
        return result
    env.record=record
    try:
        # Preserve the frozen idle exactly while respecting the physical
        # input API maximum of600 frames per recorded command.
        for offset in range(0,a.idle,600):
            env.step_input_events(frames=min(600,a.idle-offset))
        execute(env,evidence,recovery=a.recovery)
        if a.recovery and challenge["first_arrival"] is None:raise RuntimeError("Missing recovery challenge")
        require_battle_ready(base)
        for name,digest in binding.items():
            if file_hash(ROOT/name)!=digest:raise RuntimeError('Controller binding changed during probe: '+name)
    except Exception as exc:
        failure=f'{type(exc).__name__}: {exc}'
        failure_traceback=traceback.format_exc()
        print(failure,flush=True)
    finally:
        final=senses(base);final['pending_damage']=int(base.pyboy.memory[0xDB94])
        final['dungeon_items']=list(base.pyboy.memory[0xDBCC:0xDBD1])
        journal=base.journal.state()
        base.pyboy.screen.image.save(out/'final.png')
        base.close()
write(out/'evidence.json',evidence);write(out/'journal.json',journal)
write(out/'final-observations.json',list(recent_observations))
if failure_traceback:(out/'failure-traceback.txt').write_text(failure_traceback)
write(out/'challenge.json',dict(recovery=a.recovery,**challenge))
write(out/'live-result.json',dict(success=failure is None,failure=failure,final=final,commands=len(rows)))
replay=make();replay.reset(seed=0)
try:
    for index,row in enumerate(rows):
        info=apply(replay,row['command'])[4]
        if (fingerprint(replay)!=row['fingerprint'] or replay.frames!=row['frame']
            or normalized(snapshot(replay.pyboy))!=normalized(row['after']) or info['events']!=row['events']):
            raise RuntimeError(f'Replay mismatch at decision {index}')
        if index%2000==0:print(f'Fresh probe replay {index}/{len(rows)}',flush=True)
    if replay.journal.state()!=journal:raise RuntimeError('Replay journal mismatch')
    if failure is None:require_battle_ready(replay)
finally:replay.close()
write(out/'summary.json',dict(success=failure is None,failure=failure,exact_replay=True,
    final=final,commands=len(rows),qualification=qualification,case_id=a.case_id,training_eligible=False))
trajectory=str((out/'trajectory.jsonl').relative_to(ROOT))
write(out/'continuation.json',dict(start=start,replay_segments=[trajectory],
    sha256=dict(start_hashes,**{trajectory:file_hash(out/'trajectory.jsonl')}),final=final,
    control='fresh_house_guided_development',training_eligible=False))
print('FRESH HOUSE PROBE EXACT REPLAY VERIFIED',flush=True)
