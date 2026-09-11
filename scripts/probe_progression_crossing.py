"""Bounded physical diagnostics from an exactly reconstructed failed arrival.

Separate diagnostic branches, not continuation successes or training labels.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.world_memory import file_hash
from gameboy_agent.checkpoint import fingerprint
from terrain_sword import inputs


def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')


def run(out):
    source=ROOT/'runs/progression-attempt-v2'
    manifest=json.loads((source/'manifest.json').read_text())
    for name,h in manifest['artifacts'].items():
        assert file_hash(source/name)==h,name
    rows=[json.loads(line) for line in (source/'trajectory.jsonl').read_text().splitlines()]
    out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(source/'game.gbc',out/'game.gbc')
    plan=dict(source=str(source),source_trace_sha256=file_hash(source/'trajectory.jsonl'),
        purpose='Distinguish unverified passage geometry from learned movement failure.',
        branches={'north':[[1,0]]*8,'east_then_north':[[4,0]]*2+[[1,0]]*8,
                  'west_then_north':[[3,0]]*2+[[1,0]]*8},
        stop_on_any_health_loss=True,stop_on_room_change=True,stop_after_three_stationary_actions=True,
        assistance='scripted_physical_diagnostic; exact failed prefix reconstructed independently per branch')
    write(out/'plan.json',plan)
    summaries=[]
    for label,actions in plan['branches'].items():
        reference=None
        for replay in (False,True):
            env=ProgressionEnv(out/'game.gbc',source/'initial.state',max_steps=2000)
            try:
                env.reset(seed=0)
                for row in rows:
                    c=row['command'];env.step_buttons(c['buttons'],action_frames=c['action_frames'],legacy_action=c['legacy_action'])
                assert fingerprint(env)==rows[-1]['fingerprint']
                initial=snapshot(env.pyboy);terrain=inputs(env)
                grid=[terrain['objects'][r*16:r*16+10] for r in range(8)]
                physics=[[terrain['physics'][obj] for obj in line] for line in grid]
                trace=[];stationary=0;status='budget'
                for action in actions:
                    before=snapshot(env.pyboy);_,_,done,truncated,info=env.step(action);after=snapshot(env.pyboy)
                    trace.append(dict(action=action,before=before,after=after,frame=env.frames,
                                      events=info['events'],fingerprint=fingerprint(env)))
                    if after['health']<initial['health']:status='damage_stop';break
                    if after['room']!=initial['room']:status='room_crossed';break
                    stationary=stationary+1 if (before['x'],before['y'])==(after['x'],after['y']) else 0
                    if stationary>=3:status='stationary_stop';break
                    if done or truncated:status='episode_end';break
                result=dict(branch=label,status=status,initial=initial,final=snapshot(env.pyboy),trace=trace,
                            object_grid=grid,physics_grid=physics)
                if replay:
                    assert result==reference,'Diagnostic replay mismatch'
                else:
                    reference=deepcopy(result);write(out/f'{label}.json',result)
                    env.pyboy.screen.image.save(out/f'{label}.png')
            finally:env.close()
        summaries.append(dict(branch=label,status=reference['status'],actions=len(reference['trace']),
            final={k:reference['final'][k] for k in ('room','x','y','health')},exact_replay=True))
    report=dict(status='diagnostics_complete',branches=summaries,plan=plan,
                learned_policy_changed=False,new_optimizer_updates=0,
                output=str(out.relative_to(ROOT)),source_sha256=file_hash(Path(__file__)))
    write(ROOT/'reports/progression-crossing-probe-v1.json',report);print(json.dumps(summaries,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'runs/progression-crossing-probe-v1');run(p.parse_args().out.resolve())
