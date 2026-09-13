"""Full-health route development candidates; no teacher qualification claimed."""
from gameboy_agent.boss_door_route import SafeRouteSteps
from gameboy_agent.nightmare_key_route import RouteBlocker
from gameboy_agent.progression_skills import equip_item


def clear_room0d_worm(env, evidence, budget=1200):
    r=SafeRouteSteps(env)
    r.require(0x0D, lambda s: 64 <= s['x'] <= 80 and s['y'] <= 32,
              'Worm guard requires north entry lane')
    equip_item(env,4,button='b')
    if env.pyboy.memory[0xDB01] != 1:
        raise RouteBlocker('Worm guard requires sword A')
    last_swing=-32
    guard_x=72
    remote=0
    crossing=False
    for index in range(budget):
        state=r.check(13);m=env.pyboy.memory
        targets=[i for i in range(16) if m[0xC280+i] and m[0xC3A0+i]==41]
        if not targets:
            env.step_buttons([],action_frames=1)
            equip_item(env,10,button='b')
            return r.check(13)
        if len(targets)!=1:
            raise RouteBlocker('Expected one room0D worm')
        i=targets[0];dx=int(m[0xC200+i])-state['x'];dy=int(m[0xC210+i])-state['y']
        direction=('right' if dx>=0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>=0 else 'up')
        facing={'right':0,'left':1,'up':2,'down':3}[direction]
        buttons=['b']+([direction] if m[0xFF9E]!=facing else [])
        remote=remote+1 if abs(dx)+abs(dy)>40 else 0
        if remote>=80 and not crossing:
            ex,ey=int(m[0xC200+i]),int(m[0xC210+i])
            new_guard=104 if ex>=112 else 56 if ex<=40 else 72
            if new_guard!=guard_x:
                guard_x=new_guard;crossing=True
                evidence.append(dict(kind='room0d_guard_reposition',frame=env.frames,x=guard_x))
            remote=0
        if crossing or abs(dx)+abs(dy)>40:
            target_y=max(64 if guard_x!=72 else 32,min(94 if guard_x!=72 else 80,int(m[0xC210+i])))
            # Stay inside the central floor: side pits occupy x40/x120
            # at y64/80. The side guard lanes are x56/x104, not x24/x120.
            # Row64 joins these lanes below the statues.
            if crossing and abs(state['y']-64)>2:
                walk='down' if state['y']<64 else 'up'
            elif abs(state['x']-guard_x)>2:
                walk='right' if state['x']<guard_x else 'left'
            else:
                crossing=False
                walk='down' if state['y']<target_y-2 else 'up' if state['y']>target_y+2 else None
            if walk:buttons=[walk,'b']
        elif (abs(dx)<=28 and abs(dy)<=28 and m[0xFF9E]==facing
              and not m[0xC137] and index-last_swing>=24):
            buttons.append('a');last_swing=index
        if index%30==0:
            evidence.append(dict(frame=env.frames,x=state['x'],y=state['y'],enemy_x=int(m[0xC200+i]),enemy_y=int(m[0xC210+i]),buttons=buttons))
        env.step_buttons(buttons,action_frames=1)
    raise RouteBlocker('Room0D guarded encounter budget exhausted')


def clear_room0e_worm(env,evidence,budget=1800):
    r=SafeRouteSteps(env)
    r.require(14,lambda s:s['x']<=24 and 60<=s['y']<=84,'Room0E guard requires west entry')
    r.move(14,'up',lambda s:s['y']<=80,budget=8)
    equip_item(env,4,button='b')
    m=env.pyboy.memory
    if m[0xDB01]!=1:
        raise RouteBlocker('Room0E guard requires sword A')
    last_swing=-32
    region="lower";phase_route=[];remote_frames=0
    for index in range(budget):
        s=r.check(14)
        targets=[i for i in range(16) if m[0xC280+i] and m[0xC3A0+i]==41]
        if not targets:
            env.step_buttons([],action_frames=1)
            equip_item(env,10,button='b')
            return r.check(14)
        if len(targets)!=1:raise RouteBlocker('Expected one room0E worm')
        i=targets[0];dx=int(m[0xC200+i])-s['x'];dy=int(m[0xC210+i])-s['y']
        ex,ey=int(m[0xC200+i]),int(m[0xC210+i])
        remote=((region=='lower' and (ey<64 or ex<60))
                or (region=='upper' and (ey>80 or ex<48))
                or (region=='west' and ex>64))
        remote_frames=remote_frames+1 if remote and not phase_route else 0
        if remote_frames>=60:
            previous=region
            region='west' if ex<60 else ('upper' if ey<64 else 'lower')
            if region=='west':
                phase_route=([('up',80),('left',40)] if previous=='lower' else [('left',40)])
            elif region=='upper':
                phase_route=([('up',80)] if previous=='lower' else [])+[('left',40),('up',18),('right',80)]
            else:phase_route=[('left',40),('down',80),('right',88)]
            remote_frames=0
            evidence.append(dict(kind='worm_guard_region_change',frame=env.frames,region=region))
        direction=('right' if dx>=0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>=0 else 'up')
        facing={'right':0,'left':1,'up':2,'down':3}[direction]
        buttons=['b']
        if region=='lower' and s['y']<80 and s['x']<40:
            buttons=['down','b']
        elif region=='lower' and s['x']<80 and abs(dx)+abs(dy)>32:
            buttons=['right','b']
        elif abs(dx)<=22 and abs(dy)<=22 and m[0xFF9E]==facing and index-last_swing>=24:
            buttons=['a','b'];last_swing=index
        else:
            target_y=(max(18,min(108,ey)) if region=='west' else
                      (18 if region=='upper' else max(80,min(108,ey))))
            target_x=(40 if region=='west' else max(64,min(96,int(m[0xC200+i]))) if region in ('upper','west')
                      else max(88 if target_y>84 else 80,min(92,int(m[0xC200+i]))))
            tx,ty=target_x-s['x'],target_y-s['y']
            if abs(dx)>22 or abs(dy)>22:
                # Stay in the interior corridor, east of the lower-left pillar.
                if region=='lower' and s['x']<88 and target_y>84:walk='right'
                elif abs(tx)+abs(ty)>2:
                    walk=('right' if tx>0 else 'left') if abs(tx)>abs(ty) else ('down' if ty>0 else 'up')
                else:walk=direction if m[0xFF9E]!=facing else None
            else:walk=direction if m[0xFF9E]!=facing else None
            if walk:
                nx=s['x']+({'right':2,'left':-2}.get(walk,0))
                ny=s['y']+({'down':2,'up':-2}.get(walk,0))
                hazard=any(m[0xC280+j] and m[0xC3A0+j] in (22,23)
                           and abs(int(m[0xC200+j])-nx)<14 and abs(int(m[0xC210+j])-ny)<14
                           for j in range(16))
                if not hazard:buttons.insert(0,walk)
        while phase_route:
            walk,target=phase_route[0]
            value=s['x'] if walk in ('left','right') else s['y']
            done=abs(value-target)<=2
            if done:phase_route.pop(0)
            else:break
        if phase_route:
            walk,target=phase_route[0]
            if walk in ('left','right'):
                walk='right' if s['x']<target else 'left'
            else:
                walk='down' if s['y']<target else 'up'
            buttons=[walk,'b']
        if index%30==0:evidence.append(dict(frame=env.frames,x=s['x'],y=s['y'],enemy_x=int(m[0xC200+i]),enemy_y=int(m[0xC210+i]),buttons=buttons))
        env.step_buttons(buttons,action_frames=1)
    raise RouteBlocker('Room0E guard budget exhausted')
