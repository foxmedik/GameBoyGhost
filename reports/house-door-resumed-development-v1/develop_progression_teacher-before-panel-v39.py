"""Development-only state-driven progression trials with full physical replay."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from run_toadstool_progression import Trace,apply
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.world_memory import file_hash
from gameboy_agent.progression_skills import dismiss_dialogue,equip_item
from control_context import ControlContext
from run_skill_chain import SwordController,senses


def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')


def living_sword(env,evidence):
    selection=json.loads((ROOT/'configs/sword_controller.json').read_text())
    path=ROOT/selection['policy_path']
    if file_hash(path)!=selection['policy_sha256']:raise ValueError('Sword policy changed')
    policy=json.loads(path.read_text());context=ControlContext(env.env)
    controller=SwordController(context,policy)
    start=env.total_steps
    while not snapshot(env.pyboy)['sword']:
        if env.total_steps-start>=1600:raise RuntimeError('Live sword controller exceeded 1600 decisions')
        state=snapshot(env.pyboy)
        action=controller.action(senses(env.env))
        recovery=False
        if state['room']==[0,0,0xD1]:
            x,y=state['x'],state['y']
            if y<70:
                direction=(4 if x<64 else 3) if y<32 and abs(x-64)>3 else 2
            elif y<88:
                direction=3 if x>58 else 2
            else:direction=3
            action=[direction,2];recovery=True
        elif state['room']==[0,0,0xD0]:
            action=[(4 if state['x']<104 else 3) if abs(state['x']-104)>3 else 2,2]
            recovery=True
        names=(None,'up','down','left','right');buttons=(None,'a','b')
        env.step_buttons([x for x in (names[action[0]],buttons[action[1]]) if x],legacy_action=action,action_frames=3 if recovery else 10)
    dismiss_dialogue(env)
    equip_item(env,1,button='a')
    equip_item(env,4,button='b')
    evidence.append(dict(kind='live_sword_verified',frame=env.frames,state=snapshot(env.pyboy)))


def learned_mushroom_crossing(checkpoint,base):
    import torch
    from collect_progression_dagger_v1 import DURATIONS,buttons,feature,frozen_goal
    from progression_local_control import json_state
    from train_progression_dagger_v1 import DaggerNet
    saved=torch.load(checkpoint,map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);model.eval()
    def crossing(env,evidence):
        goal=frozen_goal(base);context=ControlContext(base);previous=None;stationary=0;recoveries=0;decisions=0
        for _ in range(256):
            state=json_state(snapshot(base.pyboy))
            if state['room']==[0,0,0x62]:
                evidence.append(dict(kind='learned_mushroom_crossing',frame=base.frames,decisions=decisions,recoveries=recoveries));return
            if state['room']!=[0,0,0x52] or not state['health']:raise RuntimeError(f'Learned mushroom crossing left valid state: {state["room"]}')
            raw=feature(base,context,state,goal);x=torch.from_numpy(raw.copy());n=saved['base_inputs']
            x[:n]=(x[:n]-torch.from_numpy(saved['mean']))/torch.from_numpy(saved['scale'])*torch.from_numpy(saved['input_mask'])
            with torch.no_grad():z=model(x)
            action=[int(z[:5].argmax()),int(z[5:8].argmax()),int(z[8:].argmax())]
            env.step_buttons(buttons(action),action_frames=DURATIONS[action[2]],legacy_action=action[:2]);decisions+=1
            now=json_state(snapshot(base.pyboy));pose=(now['x'],now['y']);stationary=stationary+1 if pose==previous else 0;previous=pose
            if stationary>=12:
                if recoveries>=4:raise RuntimeError(f'Learned mushroom crossing stalled at {pose}')
                env.step_buttons([('left','right','up','down')[recoveries],'b'],action_frames=3);recoveries+=1;stationary=0
        raise RuntimeError('Learned mushroom crossing budget exhausted')
    return crossing


def learned_downstream_recovery(checkpoint,base):
    import torch
    from collect_progression_dagger_v1 import DURATIONS,buttons,feature
    from collect_progression_downstream_recovery_v1 import frozen_goal,teacher_action
    from gameboy_agent.terrain_navigation import cell,exits,paths,terrain
    from progression_local_control import json_state
    from train_progression_dagger_v1 import DaggerNet
    saved=torch.load(checkpoint,map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);model.eval()
    def collision_aware_teacher(goal,recovery_index):
        action=teacher_action(base,goal,recovery_index);state=json_state(snapshot(base.pyboy));m=base.pyboy.memory
        if cell(state['x'],state['y'])==tuple(goal['cell']):return action
        threats=[(int(m[0xC200+i])-state['x'],int(m[0xC210+i])-state['y']) for i in range(16)
                 if m[0xC280+i] and m[0xC3A0+i] in (0x09,0x0B,0x14,0x1B,0xC5)]
        direction=action[0]
        blocked=any((direction==1 and -28<=dy<0 and abs(dx)<=8) or
                    (direction==2 and 0<dy<=28 and abs(dx)<=8) or
                    (direction==3 and -28<=dx<0 and abs(dy)<=8) or
                    (direction==4 and 0<dx<=28 and abs(dy)<=8) for dx,dy in threats)
        if not blocked:return action
        here=cell(state['x'],state['y']);grid=terrain(base.pyboy);options=(3,4) if direction in (1,2) else (1,2)
        candidates=[];reachable=paths(grid,here)
        for option in options:
            dx,dy={1:(0,-1),2:(0,1),3:(-1,0),4:(1,0)}[option];neighbor=(here[0]+dx,here[1]+dy)
            route=paths(grid,neighbor).get(tuple(goal['cell']))
            if neighbor in reachable and route is not None:candidates.append((len(route),option))
        return [min(candidates)[1],2,1] if candidates else action
    def recovery(env,evidence,destination):
        state=json_state(snapshot(base.pyboy))
        leg=('witch' if state['toadstool'] and not state['powder'] else
             'tarin' if not state['toadstool'] and state['powder'] and not state['tarin'] else None)
        if (state['room'][2],destination,leg) not in ((0x52,0x42,'witch'),(0x52,0x62,'tarin'),(0x54,0x44,'tarin')):
            return False
        spec={'room':state['room'][2],'target_room':destination,'leg':leg};goal=frozen_goal(base,spec)
        context=ControlContext(base);previous=None;stationary=0;recoveries=0;decisions=0
        initial_health=state['health'];teacher_mode=False;crossing_attempts=0
        for _ in range(512):
            state=json_state(snapshot(base.pyboy))
            if state['room']==goal['room']:
                evidence.append(dict(kind='learned_downstream_recovery',origin=spec['room'],target=destination,
                                     leg=leg,frame=base.frames,decisions=decisions,recoveries=recoveries));return True
            if state['room']!=[0,0,spec['room']] or not state['health']:
                raise RuntimeError(f'Learned downstream recovery left valid state: {state["room"]}')
            if not teacher_mode and (state['health'] < initial_health or decisions >= 16):
                teacher_mode=True;recoveries=1
                evidence.append(dict(kind='downstream_teacher_recovery_started',room=state['room'],
                                     target=destination,reason='damage' if state['health'] < initial_health else 'decision_bound',
                                     frame=base.frames,decisions=decisions))
            if teacher_mode and cell(state['x'],state['y'])==tuple(goal['cell']):
                crossing_attempts+=1
                if crossing_attempts>=16:
                    rejected=goal['cell'];candidates=[e for e in exits(terrain(base.pyboy),cell(state['x'],state['y']),spec['room'])
                                                     if e['direction']==goal['direction'] and e['cell']!=rejected]
                    interior=[e for e in candidates if not(e['cell'][0] in (0,9) and e['cell'][1] in (0,7))]
                    if not candidates:raise RuntimeError(f'No alternate exit after blocked crossing at {rejected}')
                    chosen=min(interior or candidates,key=lambda e:len(e['path']));goal.update(x=chosen['cell'][0]*16+8,y=chosen['cell'][1]*16+12,cell=chosen['cell']);crossing_attempts=0
                    evidence.append(dict(kind='downstream_blocked_exit_rejected',room=state['room'],
                                         target=destination,rejected=rejected,replacement=chosen['cell'],frame=base.frames))
            else:
                crossing_attempts=0
            if teacher_mode:
                action=collision_aware_teacher(goal,recoveries-1)
            else:
                raw=feature(base,context,state,goal);x=torch.from_numpy(raw.copy());n=saved['base_inputs']
                x[:n]=(x[:n]-torch.from_numpy(saved['mean']))/torch.from_numpy(saved['scale'])*torch.from_numpy(saved['input_mask'])
                with torch.no_grad():z=model(x)
                action=[int(z[:5].argmax()),int(z[5:8].argmax()),int(z[8:].argmax())]
            env.step_buttons(buttons(action),action_frames=DURATIONS[action[2]],legacy_action=action[:2]);decisions+=1
            now=json_state(snapshot(base.pyboy));pose=(now['x'],now['y']);stationary=stationary+1 if pose==previous else 0;previous=pose
            if stationary>=48 and not teacher_mode:
                teacher_mode=True;recoveries=1;stationary=0
                evidence.append(dict(kind='downstream_teacher_recovery_started',room=now['room'],
                                     target=destination,reason='stationary',frame=base.frames,decisions=decisions))
        raise RuntimeError('Learned downstream recovery budget exhausted')
    return recovery


def learned_tail_cave_key(checkpoint,base,guard=True):
    import torch
    from collect_progression_dagger_v1 import DURATIONS,buttons,history_features
    from gameboy_agent.tail_cave_controller import tail_feature
    from gameboy_agent.tail_cave_teacher import (SMALL_KEYS,HARDHAT_BEETLE,
                                                  collect_key,entities,enter_beetle_room)
    from gameboy_agent.tail_cave_recovery import DisengagingBeetleTeacher
    from progression_local_control import json_state
    from train_progression_dagger_v1 import DaggerNet
    saved=torch.load(checkpoint,map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);model.eval()
    def first_key(env,evidence):
        enter_beetle_room(env,evidence);initial_health=snapshot(base.pyboy)['health'];decisions=0
        teacher=DisengagingBeetleTeacher();teacher_mode=False;matched=0;recovery=None
        for _ in range(512):
            state=json_state(snapshot(base.pyboy))
            if int(base.pyboy.memory[SMALL_KEYS]):
                evidence.append(dict(kind='learned_tail_cave_first_key',frame=base.frames,
                                     decisions=decisions,damage_raw=initial_health-state['health'],
                                     candidate_exact_prefix=matched,teacher_recovery=recovery))
                return
            if state['room']!=[1,0,0x16] or not state['health']:
                raise RuntimeError(f'Tail Cave specialist left living room-16 contract: {state["room"]}')
            targets=entities(base,HARDHAT_BEETLE)
            if not targets:
                if teacher_mode:
                    collect_key(env,evidence)
                    continue
                raw=tail_feature(base,history_features(base.episode_actions));x=torch.from_numpy((raw-saved['mean'])/saved['scale'])
                with torch.no_grad():z=model(x)
                action=[int(z[:5].argmax()),int(z[5:8].argmax()),int(z[8:].argmax())]
                env.step_buttons(buttons(action),action_frames=DURATIONS[action[2]],legacy_action=action[:2]);decisions+=1
                continue
            teacher_buttons,teacher_frames=teacher.action(state,targets)
            teacher_action=(next(({"up":1,"down":2,"left":3,"right":4}[b] for b in teacher_buttons if b in ('up','down','left','right')),0),
                            1 if 'a' in teacher_buttons else 2 if 'b' in teacher_buttons else 0,
                            min(range(3),key=lambda i:abs(DURATIONS[i]-teacher_frames)))
            raw=tail_feature(base,history_features(base.episode_actions));x=torch.from_numpy((raw-saved['mean'])/saved['scale'])
            with torch.no_grad():z=model(x)
            action=[int(z[:5].argmax()),int(z[5:8].argmax()),int(z[8:].argmax())]
            if not teacher_mode and tuple(action)==teacher_action:
                matched+=1
            elif not teacher_mode and guard:
                teacher_mode=True;recovery=dict(frame=base.frames,decision=decisions,
                    candidate=action,teacher=list(teacher_action),state=state)
                evidence.append(dict(kind='tail_cave_teacher_recovery_started',**recovery))
            if teacher_mode:
                env.step_buttons(teacher_buttons,action_frames=teacher_frames,legacy_action=teacher_action[:2])
            else:
                env.step_buttons(buttons(action),action_frames=DURATIONS[action[2]],legacy_action=action[:2])
            decisions+=1
        raise RuntimeError('Tail Cave specialist exhausted 512-decision budget')
    return first_key


def play(out,spec,stage,local_checkpoint=None,downstream_checkpoint=None,tail_checkpoint=None,tail_guard=True,tail_followup=None):
    out.mkdir(parents=True,exist_ok=False);source=ROOT/'runs/progression-tail-cave-v12'
    for n in ('game.gbc','initial.state'):shutil.copy2(source/n,out/n)
    write(out/'plan.json',dict(spec=spec,stage=stage,split='development',optimizer_updates=0,
          sources={str(p.relative_to(ROOT)):file_hash(p) for p in [Path(__file__),*sorted((ROOT/'src/gameboy_agent').glob('*.py'))]},
          controller_config=json.loads((ROOT/'configs/sword_controller.json').read_text())))
    base=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=12288,max_frames=300000,
                        completion_milestone=None if tail_checkpoint else 'tail_cave_entered')
    rows=[];evidence=[];failure=None;began=time.monotonic()
    with (out/'trajectory.jsonl').open('x') as f:
        env=Trace(base,f,rows)
        try:
            base.reset(seed=0)
            if spec['idle']:env.step_input_events(frames=spec['idle'])
            if spec['direction']:
                env.step_input_events([spec['direction']],frames=spec['move_frames'],release_after=[spec['direction']]);env.step_input_events(frames=1)
            living_sword(env,evidence)
            if stage!='sword':
                from gameboy_agent.live_forest import execute
                execute(env,evidence)
            if stage=='quest':
                from gameboy_agent.toadstool_teacher import execute as mushroom
                from gameboy_agent.witch_approach import execute as quest
                mushroom(env,evidence,forest_crossing=(learned_mushroom_crossing(local_checkpoint,base)
                                                       if local_checkpoint else None))
                route=(learned_downstream_recovery(downstream_checkpoint,base) if downstream_checkpoint else None)
                quest(env,evidence,route_controller=route);quest(env,evidence,exchange=True,route_controller=route);quest(env,evidence,tarin=True,route_controller=route)
                quest(env,evidence,tail_key=True,route_controller=route);quest(env,evidence,tail_cave=True,route_controller=route)
                if tail_checkpoint:learned_tail_cave_key(tail_checkpoint,base,tail_guard)(env,evidence)
                if tail_followup == 'compass-room':
                    from gameboy_agent.tail_cave_progression import execute_compass_room
                    execute_compass_room(env,evidence)
        except Exception as exc:failure=f'{type(exc).__name__}: {exc}'
        finally:
            final=snapshot(base.pyboy);journal=base.journal.state();base.pyboy.screen.image.save(out/'final.png')
            with (out/'final.state').open('wb') as f:base.pyboy.save_state(f)
            base.close()
    write(out/'journal.json',journal);write(out/'evidence.json',evidence)
    replay=ProgressionEnv(out/'game.gbc',out/'initial.state',max_steps=12288,max_frames=300000,
                          completion_milestone=None if tail_checkpoint else 'tail_cave_entered')
    try:
        replay.reset(seed=0)
        for r in rows:
            info=apply(replay,r['command'])[4]
            assert fingerprint(replay)==r['fingerprint'] and snapshot(replay.pyboy)==r['after'] and info['events']==r['events'] and replay.frames==r['frame']
        assert replay.journal.state()==journal
    finally:replay.close()
    result=dict(stage=stage,spec=spec,success=failure is None,failure=failure,final=final,steps=len(rows),frames=rows[-1]['frame'],damage_raw=journal['damage_raw'],healing_raw=journal['healing_raw'],milestones=journal['milestones'],exact_replay=True,seconds=round(time.monotonic()-began,3))
    write(out/'result.json',result);write(out/'manifest.json',dict(artifacts={p.name:file_hash(p) for p in out.iterdir() if p.is_file() and p.name!='game.gbc'}))
    print(json.dumps(result),flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--stage',choices=['sword','forest','quest'],default='sword');p.add_argument('--count',type=int,default=20);p.add_argument('--case-ids',type=int,nargs='*');p.add_argument('--spec-plan',type=Path);p.add_argument('--local-controller',type=Path);p.add_argument('--downstream-controller',type=Path);p.add_argument('--tail-cave-controller',type=Path);p.add_argument('--tail-cave-unguarded',action='store_true');p.add_argument('--tail-cave-followup',choices=['compass-room']);a=p.parse_args()
    # Only development specifications are read. The existing validation panel is never loaded.
    case_ids=a.case_ids if a.case_ids is not None else range(a.count)
    if a.spec_plan:
        specification=json.loads(a.spec_plan.read_text());specs=specification['fresh_full_route_panel']['cases']
        if a.case_ids is not None:specs=[specs[i] for i in case_ids]
        else:specs=specs[:a.count]
    else:
        specs=[json.loads((ROOT/'runs/progression-longrun-hour-v1/cases'/f'development-house-{i:02d}'/'result.json').read_text())['spec'] for i in case_ids]
    frozen_sources={str(p.relative_to(ROOT)):file_hash(p) for p in
                    [Path(__file__),ROOT/'scripts/run_toadstool_progression.py',
                     *sorted((ROOT/'src/gameboy_agent').glob('*.py'))]}
    if a.spec_plan:frozen_sources[str(a.spec_plan.resolve().relative_to(ROOT))]=file_hash(a.spec_plan)
    sword_selection=json.loads((ROOT/'configs/sword_controller.json').read_text())
    navigation_selection=json.loads((ROOT/'configs/navigation_experiment.json').read_text())
    frozen_policies={sword_selection['policy_path']:sword_selection['policy_sha256'],
                     navigation_selection['policy_path']:navigation_selection['policy_sha256']}
    if a.local_controller:
        local=a.local_controller.resolve();frozen_policies[str(local.relative_to(ROOT))]=file_hash(local)
    if a.downstream_controller:
        downstream=a.downstream_controller.resolve();frozen_policies[str(downstream.relative_to(ROOT))]=file_hash(downstream)
    if a.tail_cave_controller:
        tail=a.tail_cave_controller.resolve();frozen_policies[str(tail.relative_to(ROOT))]=file_hash(tail)
    a.out.mkdir(parents=True,exist_ok=False)
    write(a.out/'panel.json',dict(schema='state-driven-teacher-development-v1',stage=a.stage,
          specs=specs,split='fresh_development' if a.spec_plan else 'development',required_successes=18,total=len(specs),
          source_hashes=frozen_sources,policy_hashes=frozen_policies,
          old_validation_panel='runs/progression-longrun-hour-v1/plan.json',
          old_validation_used_for_tuning=False,training_authorized=False,
          local_controller=str(a.local_controller) if a.local_controller else None,
          local_controller_scope='mushroom_room_52_to_62_only' if a.local_controller else None,
          downstream_controller=str(a.downstream_controller) if a.downstream_controller else None,
          downstream_controller_scope='witch_52_to_42_and_tarin_54_to_44_or_52_to_62' if a.downstream_controller else None,
          tail_cave_controller=str(a.tail_cave_controller) if a.tail_cave_controller else None,
          tail_cave_controller_scope='room_16_hardhats_and_first_small_key' if a.tail_cave_controller else None,
          tail_cave_guard=bool(a.tail_cave_controller and not a.tail_cave_unguarded),
          tail_cave_followup=a.tail_cave_followup))
    results=[]
    for spec in specs:
        for name,digest in {**frozen_sources,**frozen_policies}.items():
            if file_hash(ROOT/name)!=digest:raise RuntimeError(f'Frozen experiment changed: {name}')
        results.append(play(a.out/spec['id'],spec,a.stage,a.local_controller,a.downstream_controller,a.tail_cave_controller,not a.tail_cave_unguarded,a.tail_cave_followup))
        write(a.out/'summary.json',dict(cases=len(results),successes=sum(r['success'] for r in results),results=results))
