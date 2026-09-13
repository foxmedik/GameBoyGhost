"""Unqualified reactive Rolling Bones development controller, physical inputs only."""
from gameboy_agent.boss_door_route import SafeRouteSteps
from gameboy_agent.nightmare_key_route import RouteBlocker


def fight(env, budget=1800):
    route = SafeRouteSteps(env)
    route.check(0x11)
    m = env.pyboy.memory
    if list(m[0xDB00:0xDB02]) != [10, 1]:
        raise RouteBlocker('Rolling Bones requires feather B and sword A')
    evidence = []
    for frame in range(budget):
        state = route.check(0x11)
        active = [i for i in range(16) if m[0xC280+i]]
        bones = [i for i in active if m[0xC3A0+i] == 129]
        bars = [i for i in active if m[0xC3A0+i] == 130]
        if m[0xD911] & 0x20 and not bones and not bars and not m[0xC188]:
            env.step_buttons([], action_frames=1)
            return dict(status='miniboss_cleared', frame=env.frames, decisions=frame, evidence=evidence)
        if len(bones) > 1 or len(bars) > 1:
            raise RouteBlocker('Ambiguous Rolling Bones encounter')
        buttons = []
        x, y = state['x'], state['y']
        z = m[0xFFA2]
        danger_bar = bool(bars and abs(int(m[0xC200+bars[0]]) - x) <= 18)
        if danger_bar and z == 0:
            buttons = ['b'] if frame % 2 == 0 else []
        elif bones and m[0xC280+bones[0]] == 5:
            slot = bones[0]
            bx, by = int(m[0xC200+slot]), int(m[0xC210+slot])
            desired_y = min(112, by+22)
            if abs(x-bx) > 6:
                buttons = ['right' if x < bx else 'left']
            elif y > desired_y+1:
                buttons = ['up']
            elif y < desired_y-1:
                buttons = ['down']
            if abs(x-bx) <= 16 and 12 <= y-by <= 30:
                buttons = ['up','a'] if frame % 32 == 0 else []
            if frame % 60 == 0:
                evidence.append(dict(frame=env.frames,x=x,y=y,bx=bx,by=by,hp=int(m[0xC360+slot]),bar_x=int(m[0xC200+bars[0]]) if bars else None))
        env.step_buttons(buttons, action_frames=1)
    raise RouteBlocker(f'Rolling Bones decision budget exhausted: {evidence[-5:]}')


def fight_from_lower_lane(env, evidence, budget=3000):
    """Development alternative: hold a lane instead of pursuing across the bar."""
    route = SafeRouteSteps(env)
    route.require(0x11, lambda s: 60 <= s['x'] <= 85 and s['y'] >= 108,
                  'Lower-lane test requires the verified first-bar-crossing handoff')
    m = env.pyboy.memory
    if list(m[0xDB00:0xDB02]) != [10, 1]:
        raise RouteBlocker('Lower-lane test requires feather B and sword A')
    route.move(17, 'right', lambda s: s['x'] >= 80)
    env.step_buttons(['up'], action_frames=1)
    env.step_buttons([], action_frames=1)
    previous_hp = None
    for frame in range(budget):
        state = route.check(17)
        active = [i for i in range(16) if m[0xC280+i]]
        bones = [i for i in active if m[0xC3A0+i] == 129]
        bars = [i for i in active if m[0xC3A0+i] == 130]
        if m[0xD911] & 0x20 and not bones and not bars and not m[0xC188]:
            env.step_buttons([], action_frames=1)
            return dict(status='miniboss_cleared', frame=env.frames, decisions=frame)
        buttons = []
        bx = int(m[0xC200+bars[0]]) if bars else -999
        vx = int(m[0xC240+bars[0]]) if bars else 0
        vx = vx if vx < 128 else vx-256
        gap = bx - state['x']
        approaching = gap * vx < 0
        if bars and abs(gap) <= 20 and (approaching or abs(gap) <= 8) and m[0xFFA2] == 0:
            buttons = ['b'] if frame % 2 == 0 else []
        elif bones and m[0xC280+bones[0]] == 5:
            slot = bones[0]
            ex, ey, hp = int(m[0xC200+slot]), int(m[0xC210+slot]), int(m[0xC360+slot])
            if hp != previous_hp or frame % 120 == 0:
                evidence.append(dict(frame=env.frames, hp=hp, x=state['x'], y=state['y'], ex=ex, ey=ey, bar_x=bx, bar_vx=vx))
                previous_hp = hp
            if not (approaching and abs(gap) <= 45) and abs(ex-state['x']) <= 20 and 8 <= state['y']-ey <= 35:
                buttons = ['a'] if frame % 24 == 0 else []
        env.step_buttons(buttons, action_frames=1)
    raise RouteBlocker('Lower-lane miniboss experiment exhausted its 3000-frame budget')
