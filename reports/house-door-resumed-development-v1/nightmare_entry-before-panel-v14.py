"""Unqualified guarded third-key pickup and north departure."""
from gameboy_agent.dungeon_items import ItemSteps
from gameboy_agent.boss_door_route import SafeRouteSteps
from gameboy_agent.full_health_route import clear_room0e_worm
from gameboy_agent.feather_return import settle
from gameboy_agent.nightmare_key_route import RouteBlocker
from gameboy_agent.progression import snapshot


def third_key_and_north_exit(env,evidence):
    clear_room0e_worm(env,evidence)
    r=SafeRouteSteps(env);item=ItemSteps(env);m=env.pyboy.memory
    if m[0xDBD0]!=1 or list(m[0xDB00:0xDB02]) != [10,1]:
        raise RouteBlocker('Third key requires one key and battle loadout')
    r.move(14,'left' if snapshot(env.pyboy)['x']>40 else 'right',lambda s:38<=s['x']<=40)
    if snapshot(env.pyboy)['y']<58:r.move(14,'down',lambda s:s['y']>=58)
    else:r.move(14,'up',lambda s:s['y']<=58)
    for _ in range(180):
        s=r.check(14)
        sparks=[i for i in range(16) if m[0xC280+i] and m[0xC3A0+i]==23]
        if len(sparks)!=1:raise RouteBlocker('Expected one key-room clockwise Spark')
        i=sparks[0]
        if m[0xC240+i]>=128 and abs(int(m[0xC210+i])-s['y'])<=8 and 20<=int(m[0xC200+i])-s['x']<=30:break
        env.step_buttons([],action_frames=1)
    else:raise RouteBlocker('Key-room Spark jump window missing')
    r.move(14,'right',lambda s:s['x']>=71,jump=True)
    settle(env,14)
    env.step_buttons(['up','a'],action_frames=1)
    for _ in range(180):
        s=item.check(14,(0xAA,))
        if s['dialog_state']:break
        env.step_buttons([],action_frames=1)
    else:raise RouteBlocker('Third key receipt absent')
    if m[0xDBD0]!=2:raise RouteBlocker('Third key count incorrect')
    for _ in range(120):
        item.check(14,(0xAA,));env.step_buttons([],action_frames=1)
    env.step_buttons(['a'],action_frames=1)
    env.step_buttons([],action_frames=1)
    for index in range(120):
        s=item.check(14,(0xAA,))
        if s['x']<=43 and not s['dialog_state']:break
        env.step_input_events(['left','b'],frames=1,release_after=['b'])
        item.check(14,(0xAA,))
        env.step_input_events(frames=1)
        item.check(14,(0xAA,))
    else:raise RouteBlocker('Third key receipt escape exhausted')
    settle(env,14)
    r.move(14,'up',lambda s:s['y']<=27)
    r.move(14,'right',lambda s:s['x']>=75,jump=True)
    settle(env,14)
    r.travel(14,'up',8)
    if m[0xDBD0]!=2:raise RouteBlocker('Third key departure inventory mismatch')
    evidence.append(dict(kind='third_key_north_exit',frame=env.frames,state=snapshot(env.pyboy)))
