"""Position-checked demonstrated route guidance, with no timed command playback."""
import math
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_skills import dismiss_dialogue


def simplify(points,tolerance=2):
    if len(points)<=2:return points
    a,b=points[0],points[-1];dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
    distances=[]
    for x,y in points[1:-1]:
        u=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/den)) if den else 0
        distances.append(math.hypot(x-a[0]-u*dx,y-a[1]-u*dy))
    d=max(distances);i=distances.index(d)+1
    if d<=tolerance:return [a,b]
    return simplify(points[:i+1],tolerance)[:-1]+simplify(points[i:],tolerance)


def follow(env,rows,evidence):
    segments=[]
    for row in rows:
        s=row['before'];room=s['room']
        if not segments or segments[-1]['room']!=room:segments.append(dict(room=room,points=[]))
        segments[-1]['points'].append((s['x'],s['y']))
        if row['after']['room']!=room:
            segments[-1]['exit_direction']=next((b for b in row['command']['buttons'] if b in ('up','down','left','right')),None)
    final=rows[-1]['after']
    if segments[-1]['room']!=final['room']:segments.append(dict(room=final['room'],points=[]))
    segments[-1]['points'].append((final['x'],final['y']))
    for index,segment in enumerate(segments):
        current=snapshot(env.pyboy)
        if current['room']!=segment['room']:raise RuntimeError(f'Observed route handoff {index}: expected {segment["room"]}, got {current["room"]}')
        targets=simplify(segment['points'])
        # Arrival targets may be a few pixels across the boundary; do not turn
        # back through a doorway solely to match a historical arrival coordinate.
        targets=targets[1:] if len(targets)>1 else targets
        for tx,ty in targets:
            stationary=0;previous=None;recoveries=0
            for _ in range(128):
                s=snapshot(env.pyboy)
                if s['room']!=segment['room']:break
                if s['dialog_state']:
                    # Forest owl text can remain unskippable for longer than the
                    # generic interaction bound while it renders.
                    dismiss_dialogue(env, max_pulses=32)
                    continue
                dx,dy=tx-s['x'],ty-s['y']
                if abs(dx)<=3 and abs(dy)<=3:break
                key=('right' if dx>0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>0 else 'up')
                m=env.pyboy.memory
                nearby=[(int(m[0xC200+i])-s['x'],int(m[0xC210+i])-s['y']) for i in range(16)
                        if m[0xC280+i] and m[0xC3A0+i] in (0x09,0x0B,0x14,0xC5)
                        and abs(int(m[0xC200+i])-s['x'])+abs(int(m[0xC210+i])-s['y'])<=32]
                from terrain_sword import inputs as sword_inputs,reachable_terrain
                t=sword_inputs(env)
                cutting=reachable_terrain(x=s['x'],y=s['y'],facing=t['facing'],movement={'up':1,'down':2,'left':3,'right':4}[key],
                    indoor=t['indoor'],objects=t['objects'],physics=t['physics'],cutting_blocked=t['cutting_blocked'])
                if cutting and s['inventory'][1]==1:
                    env.step_buttons([key,'a'],action_frames=10)
                    env.step_buttons([key],action_frames=3)
                elif nearby and s['inventory'][1]==1:
                    ex,ey=min(nearby,key=lambda p:abs(p[0])+abs(p[1]))
                    face=('right' if ex>0 else 'left') if abs(ex)>abs(ey) else ('down' if ey>0 else 'up')
                    env.step_buttons([face,'a'],action_frames=10)
                    env.step_buttons([],action_frames=3)
                    evidence.append(dict(kind='observed_hostile_clearance',frame=env.frames))
                else:
                    env.step_buttons([key,'b'],action_frames=3)
                pose=(snapshot(env.pyboy)['x'],snapshot(env.pyboy)['y'])
                stationary=stationary+1 if pose==previous else 0;previous=pose
                if stationary>=12:
                    if recoveries>=4:raise RuntimeError(f'Observed route stationary in {segment["room"]} at {pose}, target {(tx,ty)}')
                    # A fine-collision corner may require lateral alignment first.
                    if key in ('up','down') and abs(dx)>1:
                        side='right' if dx>0 else 'left';amount=min(3,abs(dx))
                    elif key in ('left','right') and abs(dy)>1:
                        side='down' if dy>0 else 'up';amount=min(3,abs(dy))
                    elif key in ('up','down'):
                        side=('left','right')[recoveries%2];amount=3
                    else:
                        side=('up','down')[recoveries%2];amount=3
                    env.step_buttons([side,'b'],action_frames=amount)
                    recoveries+=1;stationary=0
                    evidence.append(dict(kind='observed_route_alignment_recovery',frame=env.frames,target=[tx,ty]))
            else:raise RuntimeError(f'Observed route point budget in {segment["room"]}, target {(tx,ty)}')
        if index+1<len(segments):
            expected=segments[index+1]['room'];a=segment['room'];b=expected
            if a[:2]!=b[:2]:raise RuntimeError('Observed route requires a separately checked doorway skill')
            delta=b[2]-a[2];direction=segment.get('exit_direction') or {-16:'up',16:'down',-1:'left',1:'right'}.get(delta)
            if direction is None:raise RuntimeError(f'Observed route unsupported transition {a}->{b}')
            for _ in range(64):
                s=snapshot(env.pyboy)
                if s['room']==expected:break
                if s['room']!=a:raise RuntimeError(f'Observed route unexpected transition {s["room"]}')
                env.step_buttons([direction,'b'],action_frames=3)
            else:raise RuntimeError(f'Observed route crossing budget {a}->{b}')
            evidence.append(dict(kind='observed_waypoint_transition',frame=env.frames,origin=a,target=b))
