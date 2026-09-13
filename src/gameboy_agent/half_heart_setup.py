"""Development-only physical half-heart setup, never a RAM health fixture."""
from gameboy_agent.progression import snapshot
from gameboy_agent.nightmare_key_route import RouteBlocker


def prepare_half_heart(env,evidence,budget=1200):
    m=env.pyboy.memory
    initial=snapshot(env.pyboy)
    if (initial['room'] != [1,0,24] or initial['health']<4
            or list(m[0xDB00:0xDB02]) != [4,1] or m[0xDBD0]!=1):
        raise RouteBlocker('Half-heart setup requires the second underground room and sword/shield')
    previous=initial['health'];last_swing=-32
    evidence.append(dict(kind='physical_half_heart_setup_start',frame=env.frames,state=initial))
    for index in range(budget):
        s=snapshot(env.pyboy);hp=s['health'];pending=int(m[0xDB94])
        if (s['room'] != [1,0,24] or s['dialog_state'] or hp<4 or hp>previous
                or hp-pending<4 or m[0xDB93] or m[0xC11C]==6):
            raise RouteBlocker('Physical half-heart setup interrupted or would undershoot health4')
        if hp != previous:
            evidence.append(dict(kind='physical_setup_health_change',frame=env.frames,
                                 before_health=previous,health=hp,pending_damage=pending))
        previous=hp
        targets=[i for i in range(16) if m[0xC280+i] and m[0xC3A0+i]==159]
        if not targets:
            if hp==4 and pending==0:
                evidence.append(dict(kind='physical_half_heart_setup_complete',frame=env.frames,state=s))
                return
            raise RouteBlocker('Goomba disappeared before actual half-heart setup completed')
        if len(targets)!=1:raise RouteBlocker('Half-heart setup requires one live Goomba')
        i=targets[0];dx=int(m[0xC200+i])-s['x'];dy=int(m[0xC210+i])-s['y']
        if pending:
            buttons=[]
        elif hp>4:
            buttons=['right' if dx>=0 else 'left'] if abs(dx)>2 else []
        else:
            direction='right' if dx>=0 else 'left';facing=0 if dx>=0 else 1
            buttons=[]
            if abs(dx)>24 or m[0xFF9E]!=facing:buttons.append(direction)
            elif abs(dy)<=20 and env.frames-last_swing>=24:
                buttons.append('a');last_swing=env.frames
        env.step_buttons(buttons,action_frames=1)
    raise RouteBlocker('Physical half-heart setup budget exhausted')
