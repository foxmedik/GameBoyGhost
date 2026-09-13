"""One bounded guided combat candidate; no qualification or training claim."""
from gameboy_agent.boss_door_route import SafeRouteSteps
from gameboy_agent.nightmare_key_route import RouteBlocker


def fight(env, evidence, budget=3000):
    r = SafeRouteSteps(env)
    r.require(17, lambda s: s['x'] <= 20 and 68 <= s['y'] <= 76,
              'Spacing candidate requires west entry')
    m = env.pyboy.memory
    if list(m[0xDB00:0xDB02]) != [10, 1] or not m[0xDBCF]:
        raise RouteBlocker('Spacing candidate requires feather B, sword A and Nightmare Key')
    for _ in range(60):
        r.check(17)
        if not m[0xC188] and not m[0xC18D]:
            break
        env.step_buttons([], action_frames=1)
    else:
        raise RouteBlocker('Entry shutters did not finish closing')
    r.move(17, 'right', lambda s: s['x'] >= 25, budget=20)
    r.move(17, 'down', lambda s: s['y'] >= 112, budget=70)
    last_swing = -100
    previous_buttons = []
    for index in range(budget):
        s = r.check(17)
        if list(m[0xDB00:0xDB02]) != [10, 1] or s['dialog_state']:
            raise RouteBlocker('Combat loadout or dialogue interruption')
        bodies = [i for i in range(16) if m[0xC280+i] and m[0xC3A0+i] == 129]
        bars = [i for i in range(16) if m[0xC280+i] and m[0xC3A0+i] == 130]
        if m[0xD911] & 0x20 and not bodies and not bars:
            env.step_buttons([], action_frames=1)
            r.check(17)
            # Opening can begin on this very step after the kill flag changes.
            # Inspect the resulting state rather than returning a stale check.
            if not m[0xC188] and not m[0xC18C] and not m[0xC18D]:
                return dict(success=True, frame=env.frames, combat_decisions=index+1)
            continue
        if len(bodies) > 1 or len(bars) > 1:
            raise RouteBlocker('Ambiguous combat entities')
        x, y = s['x'], s['y']
        body = bodies[0] if bodies else None
        ex, ey = (int(m[0xC200+body]), int(m[0xC210+body])) if body is not None else (80, 80)
        bar = bars[0] if bars else None
        bx = int(m[0xC200+bar]) if bar is not None else -999
        bv = int(m[0xC240+bar]) if bar is not None else 0
        bv = bv if bv < 128 else bv-256
        gap = bx-x
        bar_near = bar is not None and abs(gap) <= 20 and (gap*bv < 0 or abs(gap) <= 8)
        body_near = body is not None and abs(ex-x) <= 20 and abs(ey-y) <= 18
        buttons = []
        target_y = max(96, min(112, ey+24))
        if body_near and y < 112:
            buttons = ['down']
        elif abs(x-80) > 1:
            buttons = ['right' if x < 80 else 'left']
        elif y < target_y-1:
            buttons = ['down']
        elif y > target_y+1 and not bar_near:
            buttons = ['up']
        if (bar_near or body_near) and m[0xFFA2] == 0 and 'b' not in previous_buttons:
            buttons += ['b']
        if (body is not None and m[0xC280+body] == 5
                and abs(ex-x) <= 18 and 12 <= y-ey <= 30
                and index-last_swing >= 24 and not m[0xC420+body]
                and not body_near):
            buttons = ['up', 'a'] + (['b'] if 'b' in buttons else [])
            last_swing = index
        if index % 10 == 0 or 'a' in buttons or 'b' in buttons:
            evidence.append(dict(frame=env.frames, x=x, y=y, z=int(m[0xFFA2]),
                body_x=ex, body_y=ey, body_z=int(m[0xC310+body]) if body is not None else None,
                hp=int(m[0xC360+body]) if body is not None else None,
                body_status=int(m[0xC280+body]) if body is not None else None,
                bar_x=bx, bar_vx=bv, buttons=buttons))
        env.step_buttons(buttons, action_frames=1)
        previous_buttons = buttons
    raise RouteBlocker('Observed spacing exhausted its 3000-decision combat budget')
