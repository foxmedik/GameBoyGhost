"""Interactive physical development continuation; all inputs recorded and replayed."""
import json
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.world_memory import file_hash
from collect_room15_overnight import senses, normalized, write
from run_toadstool_progression import Trace, apply

parser=argparse.ArgumentParser()
parser.add_argument('--handoff', default='runs/room15-entry-fallback-check/continuation.json')
parser.add_argument('--output', default='runs/tail-cave-onward-v1')
args=parser.parse_args()
out=ROOT/args.output
out.mkdir(exist_ok=False)
handoff=json.loads((ROOT/args.handoff).read_text())
for p,h in handoff['sha256'].items():
    if file_hash(ROOT/p)!=h: raise RuntimeError(f'Changed source: {p}')
def make():
    return ProgressionEnv(ROOT/handoff['start']['rom'],ROOT/handoff['start']['initial_state'],
                          max_steps=24000,max_frames=400000,completion_milestone=None)
def checked(env,row):
    info=apply(env,row['command'])[4]
    if (fingerprint(env)!=row['fingerprint'] or env.frames!=row['frame']
            or normalized(snapshot(env.pyboy))!=normalized(row['after']) or info['events']!=row['events']):
        raise RuntimeError(f'Replay mismatch {row["decision"]}')
prefix=[]
for p in handoff['replay_segments']:
    prefix.extend(json.loads(l) for l in (ROOT/p).read_text().splitlines())
env=make();env.reset(seed=0)
for index,row in enumerate(prefix):
    checked(env,row)
    if index%2000==0: print(f'Prefix replay {index}/{len(prefix)}',flush=True)
failures=[]
rows=[];stream=(out/'trajectory.jsonl').open('x');tr=Trace(env,stream,rows)
def show():
    env.pyboy.screen.image.save(out/'current.png')
    print(json.dumps(senses(env)),flush=True)
show()
print('READY',flush=True)
for line in sys.stdin:
    request=json.loads(line)
    with (out/'requests.jsonl').open('a') as log: log.write(json.dumps(request)+'\n')
    if request.get('finish'):
        final=senses(env);final['pending_damage']=int(env.pyboy.memory[0xDB94]);final['dungeon_items']=list(env.pyboy.memory[0xDBCC:0xDBD1]);journal=env.journal.state();stream.close();env.pyboy.screen.image.save(out/'final.png');env.close()
        replay=make();replay.reset(seed=0)
        for index,row in enumerate(prefix+rows):
            checked(replay,row)
            if index%2000==0: print(f'Independent replay {index}/{len(prefix)+len(rows)}',flush=True)
        if replay.journal.state()!=journal:raise RuntimeError('Final journal differs')
        replay.close()
        outcome=('terminal_failure' if not final['state']['health'] else
                 'interrupted_pending_damage' if final['pending_damage'] else 'alive')
        write(out/'summary.json',dict(status='complete',outcome=outcome,exact_replay=True,extension_commands=len(rows),final=final,
             control='guided_physical_development',validation_loaded=False,training_eligible=False,blockers=failures))
        write(out/'continuation.json',dict(handoff,status='verified_guided_continuation' if outcome=='alive' else 'verified_interrupted_trace_not_resumable',final=final,evidence=str((out/'summary.json').relative_to(ROOT)),control='guided_physical_development',replay_segments=handoff['replay_segments']+[str((out/'trajectory.jsonl').relative_to(ROOT))],sha256=dict(handoff['sha256'],**{str((out/'trajectory.jsonl').relative_to(ROOT)):file_hash(out/'trajectory.jsonl')}),
             milestones=dict(handoff.get('milestones', {}), map=bool(final['dungeon_items'][0]), compass=bool(final['dungeon_items'][1]), nightmare_key=bool(final['dungeon_items'][3]), small_keys_held=final['dungeon_items'][4]),
             training_eligible=False, segment_note='Replay every listed segment in order from the original house state; development traces are not a reusable controller.'))
        print('EXACT REPLAY VERIFIED',flush=True);break
    try:
        exec(request['code'])
        show()
    except Exception as exc:
        failures.append(dict(frame=env.frames, error=f'{type(exc).__name__}: {exc}'))
        print(f'{type(exc).__name__}: {exc}',flush=True);show()
