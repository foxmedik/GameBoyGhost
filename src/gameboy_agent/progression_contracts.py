"""Read-only stage contracts: an invalid handoff never starts navigation."""
from gameboy_agent.progression import snapshot, mode


class StageBlocked(RuntimeError):
    def __init__(self, stage, reason, state):
        self.stage, self.reason, self.state = stage, reason, state
        super().__init__(f'{stage} precondition failed: {reason}; room={state["room"]}, '
                         f'position=({state["x"]},{state["y"]}), health={state["health"]}')


ROOMS = {'toadstool':[0,0,0x52], 'witch-approach':[0,0,0x50],
         'witch-exchange':[0,0,0x62], 'tarin':[1,14,0xA2],
         'tail-key':[0,0,0x51], 'tail-cave':[0,0,0x41]}


def require_stage(env, stage):
    s=snapshot(env.pyboy)
    reasons=[]
    if s['room']!=ROOMS[stage]:reasons.append(f'expected room {ROOMS[stage]}')
    if s['health']<=0:reasons.append('living player required')
    if mode(s) not in ('world','dialogue'):reasons.append('settled gameplay required')
    if not s['sword'] or 1 not in s['inventory']:reasons.append('physically acquired sword required')
    if stage in ('witch-approach','witch-exchange') and s['toadstool']!=1:
        reasons.append('toadstool possession required')
    if stage=='tarin' and (s['toadstool'] or s['powder']<=0 or 12 not in s['inventory']):
        reasons.append('usable powder required')
    if stage=='tail-key' and not s['tarin']:reasons.append('Tarin cure required')
    if stage=='tail-cave' and not s['tail_key']:reasons.append('Tail Key possession required')
    if reasons:raise StageBlocked(stage,'; '.join(reasons),s)
    return s


def settle_and_require_stage(env, stage, *, frames=600):
    """Allow an in-flight physical transition to settle, then check the contract."""
    from gameboy_agent.transitions import BUTTONS
    for _ in range(frames):
        state = snapshot(env.pyboy)
        if mode(state) in ('world', 'dialogue'):
            break
        env.step_input_events(release=BUTTONS, frames=1)
    return require_stage(env, stage)


def adjacent_direction(source,destination):
    if source[:2]!=[0,0] or not 0<=destination<256:
        raise StageBlocked('route','overworld room required',dict(room=source,x=0,y=0,health=1))
    dx,dy=destination%16-source[2]%16,destination//16-source[2]//16
    directions={(0,-1):(1,'up'),(0,1):(2,'down'),(-1,0):(3,'left'),(1,0):(4,'right')}
    if (dx,dy) not in directions:
        raise StageBlocked('route',f'nonadjacent destination {destination:02X}',dict(room=source,x=0,y=0,health=1))
    return directions[dx,dy]
