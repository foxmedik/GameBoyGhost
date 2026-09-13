"""Unqualified physical Feather return and floating-heart recovery candidate."""
from gameboy_agent.boss_door_route import SafeRouteSteps
from gameboy_agent.nightmare_key_route import RouteBlocker
from gameboy_agent.progression import snapshot


def settle(env,room,budget=90):
    r=SafeRouteSteps(env);m=env.pyboy.memory
    for _ in range(budget):
        r.check(room)
        if not m[0xFFA2] and not m[0xC11C] and not m[0xDB93] and not m[0xDB94]:
            env.step_buttons([],action_frames=1)
            r.check(room)
            if not any(m[a] for a in (0xFFA2,0xC11C,0xDB93,0xDB94)):
                return
            continue
        env.step_buttons([],action_frames=1)
    raise RouteBlocker('Feather return did not settle')


def return_to_underground(env,evidence):
    r=SafeRouteSteps(env);m=env.pyboy.memory
    r.require(29,lambda s:68<=s['x']<=76 and s['y']<=60,
              'Feather return requires closed chest approach')
    if list(m[0xDB00:0xDB02]) != [10,1] or m[0xDBD0]!=1:
        raise RouteBlocker('Feather return requires battle loadout and one key')
    r.move(29,'down',lambda s:s['y']>=78)
    r.move(29,'down',lambda s:s['y']>=114,jump=True)
    settle(env,29)
    r.travel(29,'down',28)
    r.move(28,'down',lambda s:s['y']>=65)
    initial_health=snapshot(env.pyboy)['health']
    for index in range(16):
        r.check(28)
        env.step_buttons(['down']+(['b'] if index==0 else []),action_frames=1)
    settle(env,28)
    if m[0xDB5A] != 8*m[0xDB5B]:
        raise RouteBlocker('Floating heart did not restore full health')
    evidence.append(dict(kind='floating_heart_return',before_health=initial_health,
                         frame=env.frames,state=snapshot(env.pyboy)))
    r.travel(28,'down',1)
    r.travel(1,'down',24)
    evidence.append(dict(kind='full_health_underground_return',frame=env.frames,state=snapshot(env.pyboy)))


def platform_jump(env,room,frames):
    r=SafeRouteSteps(env)
    if env.pyboy.memory[0xDB00]!=10:raise RouteBlocker('Platform jump requires Feather B')
    for index in range(frames):
        r.check(room)
        env.step_buttons(['right','b'],action_frames=1)
    r.check(room)


def underground_return_to_main(env,evidence):
    r=SafeRouteSteps(env);m=env.pyboy.memory
    r.require(24,lambda s:s['x']==40 and s['y']<=20,'Return requires west upper ladder')
    if list(m[0xDB00:0xDB02]) != [10,1] or m[0xDBD0]!=1:
        raise RouteBlocker('Underground return requires battle loadout and one key')
    r.move(24,'down',lambda s:s['y']>=64)
    r.move(24,'right',lambda s:s['x']>=70)
    platform_jump(env,24,32)
    r.move(24,'right',lambda s:s['x']>=130)
    r.travel(24,'right',25)
    platform_jump(env,25,36)
    for _ in range(8):
        r.check(25);env.step_buttons([],action_frames=1)
    r.move(25,'right',lambda s:s['x']>=71)
    platform_jump(env,25,32)
    for _ in range(8):
        r.check(25);env.step_buttons([],action_frames=1)
    r.move(25,'right',lambda s:s['x']>=120)
    r.travel(25,'up',3)
    if m[0xDB5A]!=8*m[0xDB5B] or m[0xDBD0]!=1:
        raise RouteBlocker('Main dungeon return inventory or health mismatch')
    evidence.append(dict(kind='main_dungeon_return',frame=env.frames,state=snapshot(env.pyboy)))


def return_to_room0e(env,evidence):
    from gameboy_agent.full_health_route import clear_room0d_worm
    r=SafeRouteSteps(env)
    r.require(3,lambda s:128<=s['x']<=144 and s['y']<=40,'Main return requires east stairs')
    r.move(3,'down',lambda s:s['y']>=48)
    r.travel(3,'right',4)
    r.move(4,'right',lambda s:s['x']>=24)
    r.move(4,'down',lambda s:s['y']>=80)
    r.move(4,'right',lambda s:s['x']>=48)
    r.move(4,'down',lambda s:s['y']>=112,jump=True)
    settle(env,4)
    r.move(4,'right',lambda s:s['x']>=80)
    r.travel(4,'down',7)
    r.move(7,'down',lambda s:s['y']>=40)
    r.move(7,'left',lambda s:s['x']<=70)
    # Clear the live Keese from the safe north side before jumping the trap.
    m=env.pyboy.memory
    last_swing=-32
    for index in range(600):
        s=r.check(7)
        bats=[i for i in range(16) if m[0xC280+i] and m[0xC3A0+i]==25]
        if not bats:break
        active=[i for i in bats if m[0xC280+i]==5]
        buttons=[]
        if active:
            i=min(active,key=lambda i:abs(int(m[0xC200+i])-s['x'])+abs(int(m[0xC210+i])-s['y']))
            dx,dy=int(m[0xC200+i])-s['x'],int(m[0xC210+i])-s['y']
            face=('right' if dx>=0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>=0 else 'up')
            if m[0xFF9E]!={'right':0,'left':1,'up':2,'down':3}[face]:buttons=[face]
            elif abs(dx)<=24 and abs(dy)<=24 and index-last_swing>=24:
                buttons=['a'];last_swing=index
        env.step_buttons(buttons,action_frames=1)
    else:raise RouteBlocker('North-side room07 Keese clearance budget exhausted')
    evidence.append(dict(kind='room07_return_keese_cleared',frame=env.frames))
    r.move(7,'down',lambda s:s['y']>=48)
    r.move(7,'down',lambda s:s['y']>=82,jump=True)
    settle(env,7)
    from gameboy_agent.progression_skills import equip_item
    equip_item(env,4,button='b')
    r.check(7)
    r.travel(7,'down',13)
    clear_room0d_worm(env,evidence)
    r.move(13,'down',lambda s:s['y']>=68)
    r.move(13,'right',lambda s:s['x']>=103)
    r.move(13,'right',lambda s:s['x']>=139,jump=True)
    settle(env,13)
    r.travel(13,'right',14)
    evidence.append(dict(kind='room0e_return',frame=env.frames,state=snapshot(env.pyboy)))
