"""Bounded physical approaches with explicit room/position checks."""
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_skills import dismiss_dialogue
from gameboy_agent.terrain_navigation import cell,paths,steer_path
from gameboy_agent.transitions import BUTTONS


def approach(env,target,grid_reader,*,expected=None,budget=256,shield=True):
    origin=snapshot(env.pyboy)['room'];previous=None;stationary=0
    for _ in range(budget):
        s=snapshot(env.pyboy)
        if s['room']!=origin:
            if s['room']==expected:return
            raise RuntimeError(f'Approach room changed: {origin} -> {s["room"]}')
        if s['dialog_state']:dismiss_dialogue(env);continue
        tx,ty=target[0]*16+8,target[1]*16+12
        if abs(s['x']-tx)<=3 and abs(s['y']-ty)<=3:return
        here=cell(s['x'],s['y']);route=paths(grid_reader(env.pyboy),here).get(tuple(target))
        if route is None:raise RuntimeError(f'No approach path in {origin} from {here} to {target}')
        direction=steer_path(s['x'],s['y'],route[0] if route else target)
        keys=[(None,'up','down','left','right')[direction]]
        if shield and s['room'][0]==0:
            if s['inventory'][0]==4:keys.append('b')
            elif s['inventory'][1]==4:keys.append('a')
        env.step_buttons(keys,action_frames=3)
        now=snapshot(env.pyboy);pose=(now['x'],now['y'])
        stationary=stationary+1 if previous==pose else 0;previous=pose
        if stationary>=32:raise RuntimeError(f'Approach stationary in {origin} at {pose} toward {target}')
    raise RuntimeError(f'Approach budget exhausted in {origin} toward {target}')


def cross(env,direction,expected,*,budget=64):
    origin=snapshot(env.pyboy)['room']
    for _ in range(budget):
        s=snapshot(env.pyboy)
        if s['room']==expected:return
        if s['room']!=origin:raise RuntimeError(f'Unexpected crossing {origin} -> {s["room"]}, expected {expected}')
        keys=[direction]
        if s['room'][0]==0 and s['inventory'][0]==4:keys.append('b')
        env.step_buttons(keys,action_frames=3)
    raise RuntimeError(f'Crossing budget exhausted: {origin} -> {expected}')
