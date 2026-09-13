"""Guided development return from Nightmare Key; not a qualified teacher."""
from gameboy_agent.boss_door_route import SafeRouteSteps, armed_move
from gameboy_agent.nightmare_key_route import RouteBlocker


def reach_rolling_bones(env):
    r = SafeRouteSteps(env)
    r.require(8, lambda s: 70 <= s['x'] <= 72 and 40 <= s['y'] <= 41,
              'Return requires the closed Nightmare Key receipt handoff')
    m = env.pyboy.memory
    if not m[0xDBCF] or m[0xDBD0] != 1 or list(m[0xDB00:0xDB02]) != [10, 1]:
        raise RouteBlocker('Return requires Nightmare Key, one Small Key, feather B and sword A')
    r.move(8, 'right', lambda s: s['x'] >= 124)
    r.travel(8, 'right', 9)
    r.move(9, 'right', lambda s: s['x'] >= 40)
    r.move(9, 'down', lambda s: s['y'] >= 96)
    r.move(9, 'right', lambda s: s['x'] >= 64)
    r.move(9, 'right', lambda s: s['x'] >= 116, jump=True)
    r.move(9, 'right', lambda s: s['x'] >= 120)
    r.travel(9, 'down', 15)
    armed_move(env, 15, 'down', lambda s: s['y'] >= 32, reactive_enemies=True)
    armed_move(env, 15, 'left', lambda s: s['x'] <= 25, reactive_enemies=True)
    r.move(15, 'down', lambda s: s['y'] >= 48)
    r.travel(15, 'left', 14)
    r.move(14, 'left', lambda s: s['x'] <= 136)
    r.move(14, 'down', lambda s: s['y'] >= 81, jump=True)
    r.travel(14, 'right', 15)
    r.move(15, 'right', lambda s: s['x'] >= 25)
    r.move(15, 'down', lambda s: s['y'] >= 110)
    armed_move(env, 15, 'right', lambda s: s['x'] >= 135, reactive_enemies=True)
    armed_move(env, 15, 'up', lambda s: s['y'] <= 72, reactive_enemies=True)
    r.travel(15, 'right', 16)
    if m[0xDBD0] != 0:
        raise RouteBlocker('East door did not spend exactly one Small Key')
    return cross_room10_with_stalfos(env)


def cross_room10_with_stalfos(env):
    """Development north passage accounting for the live evasive Stalfos."""
    r = SafeRouteSteps(env)
    r.require(16, lambda s: s['x'] <= 20 and 68 <= s['y'] <= 76,
              'Room10 crossing requires west entry')
    m = env.pyboy.memory
    if not m[0xDBCF] or list(m[0xDB00:0xDB02]) != [10, 1]:
        raise RouteBlocker('Crossing requires Nightmare Key, feather B and sword A')
    r.move(16, 'right', lambda s: s['x'] >= 25)
    for direction, done in [('up', lambda s: s['y'] <= 40),
                            ('right', lambda s: s['x'] >= 88)]:
        # Allow bounded close-combat pauses in addition to passage movement.
        for _ in range(360):
            s = r.check(16)
            if done(s):
                env.step_buttons([], action_frames=1)
                break
            near_stalfos = any(m[0xC280+i]==5 and m[0xC3A0+i] == 30
                and abs(int(m[0xC200+i])-s['x']) < 36
                and abs(int(m[0xC210+i])-s['y']) < 36 for i in range(16))
            lane_direction=('down' if s['y']<40 else 'up' if s['y']>42 else direction) if direction=='right' else direction
            buttons=[lane_direction] + (['a'] if near_stalfos else [])
            close=[i for i in range(16) if m[0xC280+i]==5 and m[0xC3A0+i]==30
                   and abs(int(m[0xC200+i])-s['x'])<=18
                   and abs(int(m[0xC210+i])-int(m[0xC310+i])-s['y'])<=18]
            if close:
                i=min(close,key=lambda i:abs(int(m[0xC200+i])-s['x'])+abs(int(m[0xC210+i])-int(m[0xC310+i])-s['y']))
                dx=int(m[0xC200+i])-s['x'];dy=int(m[0xC210+i])-int(m[0xC310+i])-s['y']
                aim=('right' if dx>=0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>=0 else 'up')
                facing={'right':0,'left':1,'up':2,'down':3}[aim]
                # Stop advancing into a nearby enemy while a wrongly aimed
                # swing settles; turn before issuing the next sword press.
                buttons=[] if m[0xC137] else [aim] if m[0xFF9E]!=facing else ['a']
            env.step_buttons(buttons, action_frames=1)
        else:
            raise RouteBlocker('Stalfos north passage budget exhausted')
    # Sword swings block walking; settle the final Stalfos swing before
    # observing a Spark crossing window or applying the movement watchdog.
    for _ in range(48):
        r.check(16)
        if not m[0xC137] and not m[0xC121]:break
        env.step_buttons([],action_frames=1)
    else:raise RouteBlocker('Room10 sword animation did not settle')
    r.move(16, 'up', lambda s: s['y'] <= 40)
    r.move(16, 'right', lambda s: s['x'] >= 88)
    # Use the interior edge below the outer Spark's y29 path. Turning
    # during a top-down jump preserves horizontal momentum into the pit.
    r.move(16, 'down', lambda s: s['y'] >= 40)
    # The outer Spark climbs x108 before crossing the launch lane. Wait
    # for its observed rightward clearance before approaching the jump.
    for _ in range(700):
        s=r.check(16)
        sparks=[i for i in range(16) if m[0xC280+i]==5 and m[0xC3A0+i]==23]
        if len(sparks)!=1:raise RouteBlocker('Expected one outer room10 Spark')
        i=sparks[0]
        if m[0xC200+i]>=120 and m[0xC210+i]<=40 and 0<m[0xC240+i]<128:
            break
        enemies=[i for i in range(16) if m[0xC280+i]==5 and m[0xC3A0+i]==30
                 and abs(int(m[0xC200+i])-s['x'])<=28
                 and abs(int(m[0xC210+i])-int(m[0xC310+i])-s['y'])<=28]
        buttons=[]
        if enemies and not m[0xC137]:
            i=enemies[0];dx=int(m[0xC200+i])-s['x'];dy=int(m[0xC210+i])-int(m[0xC310+i])-s['y']
            aim=('right' if dx>=0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>=0 else 'up')
            face={'right':0,'left':1,'up':2,'down':3}[aim]
            buttons=[aim] if m[0xFF9E]!=face else ['a']
        env.step_buttons(buttons,action_frames=1)
    else:raise RouteBlocker('Room10 outer Spark clearance budget exhausted')
    r.move(16, 'right', lambda s: s['x'] >= 104)
    # Diagonal momentum lasts through landing: launch at y40 to land at y72.
    if m[0xFFA2] or m[0xC11C]:
        raise RouteBlocker('Southeast jump requires grounded movement')
    for index in range(60):
        s = r.check(16)
        if s['x'] >= 136 and s['y'] >= 64 and not m[0xFFA2] and not m[0xC11C]:
            break
        buttons = ['right'] + (['down'] if s['y'] < 72 else [])
        env.step_buttons(buttons + (['b'] if index == 0 else []), action_frames=1)
    else:
        raise RouteBlocker('Southeast jump budget exhausted')
    # Align only after the observed grounded landing on the east ledge.
    for _ in range(45):
        r.check(16)
        if not m[0xFFA2] and not m[0xC11C]:
            break
        env.step_buttons([], action_frames=1)
    else:
        raise RouteBlocker('East ledge landing did not settle')
    armed_move(env,16,'up',lambda s:s['y']<=72,budget=96,reactive_stalfos=True)
    armed_move(env,16,'right',lambda s:s['x']>=150,budget=180,reactive_enemies=True)
    return r.travel(16, 'right', 17)
