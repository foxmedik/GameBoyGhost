"""Bounded, physically replayed terrain-planning extension of the safe D0 prefix."""
from collections import Counter
from copy import deepcopy
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.terrain_navigation import terrain,cell,paths,choose_exit,steer,component
from gameboy_agent.world_memory import WorldMemory,file_hash
from gameboy_agent.checkpoint import fingerprint
from terrain_sword import inputs as sword_inputs, reachable_terrain, CUTTABLE


def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')


def run(regions=False,cut_flora=False,out_name=None):
    source=ROOT/'runs/progression-attempt-v4';out=ROOT/('runs/progression-forest-terrain-v3' if cut_flora else 'runs/progression-forest-terrain-v2' if regions else 'runs/progression-forest-terrain-v1');out=ROOT/'runs'/out_name if out_name else out;out.mkdir(exist_ok=False)
    manifest=json.loads((source/'manifest.json').read_text())
    for name,h in manifest['artifacts'].items():assert file_hash(source/name)==h,name
    prefix=[json.loads(l) for l in (source/'trajectory.jsonl').read_text().splitlines()]
    for name in ('game.gbc','initial.state'):shutil.copy2(source/name,out/name)
    write(out/'plan.json',dict(source=str(source),source_hash=file_hash(source/'trajectory.jsonl'),
        region_aware=regions,cut_flora=cut_flora,extension_budget=1600,action_frames=3,target_room=0x50,stop_after_damage_raw=4,
        max_stationary=64,max_rejected_exits=6,assistance='read_only_rom_physics_plus_overworld_grid_and_toadstool_room_hint',
        supervision='scripted_local_terrain_planner_with_physical_equipped_shield',
        passage_constraints='No assumed reverse crossings; candidate room identity verified on actual transition.'))
    reference=None
    for replay in (False,True):
        env=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=2500)
        try:
            env.reset(seed=0)
            for row in prefix:
                c=row['command'];env.step_buttons(c['buttons'],action_frames=c['action_frames'],legacy_action=c['legacy_action'])
            assert fingerprint(env)==prefix[-1]['fingerprint']
            initial=snapshot(env.pyboy);visits=Counter({0xD0:1});rejected=set();chosen=None;waypoints=[]
            trace=[];decisions=[];stationary=0;status='budget';last_room=initial['room']
            known_grids={};region_visits=Counter();last_region=None
            for step in range(1600):
                s=snapshot(env.pyboy);room=s['room'][2]
                if s['toadstool']:status='toadstool_acquired';break
                if s['room'][:2]!=[0,0]:status='indoor_transition_requires_skill';break
                if s['dialog_state']:
                    action=[0,step%2]
                    decision=dict(kind='dialogue_advance')
                else:
                    grid=terrain(env.pyboy)
                    raw_grid=deepcopy(grid)
                    if cut_flora:
                        t=sword_inputs(env)
                        for ry in range(8):
                            for cx in range(10):
                                if t['objects'][ry*16+cx] in CUTTABLE[False] and grid[ry][cx]==0x30:
                                    grid[ry][cx]=6  # Planning allowance only; physically cut before moving.
                    known_grids[room]=grid
                    region=(room,component(grid,cell(s['x'],s['y'])))
                    if region!=last_region:region_visits[region]+=1;last_region=region
                    if chosen is None:
                        if room==0x50:
                            route=paths(grid,cell(s['x'],s['y'])).get((2,3))
                            if route is None:status='toadstool_approach_requires_obstacle_skill';break
                            chosen=dict(direction=0,cell=[2,3],expected_room=room);waypoints=[list(cell(s['x'],s['y']))]+[list(p) for p in route]
                        else:
                            chosen=choose_exit(grid,cell(s['x'],s['y']),room,0x50,region_visits if regions else visits,rejected,known_grids if regions else None)
                            if chosen is None:status='no_conservative_exit_path';break
                            waypoints=[list(cell(s['x'],s['y']))]+chosen['path']
                        decisions.append(dict(decision=env.total_steps,room=room,chosen=deepcopy(chosen),physics=raw_grid,planning_physics=grid))
                    while waypoints and steer(s['x'],s['y'],waypoints[0]) is None:waypoints.pop(0)
                    movement=steer(s['x'],s['y'],waypoints[0]) if waypoints else chosen['direction']
                    if not movement:status='interaction_required_at_toadstool';break
                    shield=1 if s['inventory'][1]==4 else 2 if s['inventory'][0]==4 else 0
                    if not shield:status='shield_not_equipped';break
                    sword_button=1 if s['inventory'][1]==1 else 2 if s['inventory'][0]==1 else 0
                    cutting=None
                    if cut_flora and sword_button:
                        t=sword_inputs(env)
                        cutting=reachable_terrain(x=s['x'],y=s['y'],facing=t['facing'],movement=movement,
                            indoor=t['indoor'],objects=t['objects'],physics=t['physics'],cutting_blocked=t['cutting_blocked'])
                    action=[movement,(sword_button if step%2==0 else 0) if cutting else shield];decision=dict(kind='terrain_path',target=deepcopy(chosen),next_cell=waypoints[0] if waypoints else None,cutting=cutting)
                names=(None,'up','down','left','right');buttons=(None,'a','b')
                _,_,done,truncated,info=env.step_buttons([v for v in (names[action[0]],buttons[action[1]]) if v],action_frames=3,legacy_action=action)
                after=snapshot(env.pyboy)
                trace.append(dict(decision=env.total_steps-1,command=deepcopy(env.episode_actions[-1]),before=s,after=after,
                    events=info['events'],frame=env.frames,fingerprint=fingerprint(env),planner_decision=decision))
                if after['room']!=last_room:
                    visits[after['room'][2]]+=1;last_room=after['room'];chosen=None;waypoints=[];stationary=0
                else:
                    stationary=stationary+1 if (s['x'],s['y'])==(after['x'],after['y']) else 0
                if stationary>=64:
                    if chosen is not None:rejected.add((room,chosen['direction'],tuple(chosen['cell'])))
                    chosen=None;waypoints=[];stationary=0
                    if len(rejected)>=6:status='repeated_geometry_mismatch';break
                if initial['health']-after['health']>=4:status='damage_budget';break
                if done or truncated:status='episode_end';break
            value=dict(status=status,trace=trace,route_decisions=decisions,final=snapshot(env.pyboy),
                journal=env.journal.state(),rooms=dict(visits),rejected=sorted(rejected))
            if replay:assert value==reference,'Terrain planner/action replay mismatch'
            else:
                reference=deepcopy(value);env.pyboy.screen.image.save(out/'final.png')
                with (out/'final.state').open('wb') as f:env.pyboy.save_state(f)
        finally:env.close()
    (out/'trajectory.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in prefix+reference['trace']))
    write(out/'journal.json',reference['journal']);write(out/'route-decisions.json',reference['route_decisions'])
    result=dict(status=reference['status'],steps=len(prefix)+len(reference['trace']),extension_steps=len(reference['trace']),
        extension_damage_raw=initial['health']-reference['final']['health'],rooms=reference['rooms'],final=reference['final'],
        exact_action_replay=True,assistance='scripted_live_terrain_navigation_with_source_grounded_goal_hint',quest_success=False)
    write(out/'result.json',result)
    write(out/'manifest.json',dict(artifacts={p.name:file_hash(p) for p in out.iterdir() if p.is_file() and p.name!='game.gbc'}))
    m=WorldMemory.load(ROOT/'runs/progression-crossing-resolution-v1/memory-generation-3.json').next_generation()
    m.import_verified_fixture(out);m.verify_evidence();m.save(out/'memory-generation-4.json')
    write(ROOT/'reports'/f'{out.name}.json',dict(result=result,output=str(out.relative_to(ROOT)),memory_version=m.version))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--regions',action='store_true');p.add_argument('--cut-flora',action='store_true');p.add_argument('--out-name');args=p.parse_args();run(args.regions or args.cut_flora,args.cut_flora,args.out_name)
