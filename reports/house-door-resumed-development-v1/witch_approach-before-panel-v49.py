"""Bounded physical return from the toadstool clearing toward the witch.

Room order is supplied guide assistance. Traversal uses current object physics;
unreachable geometry is a reported blocker, never a state load or RAM edit.
"""
from gameboy_agent.progression import snapshot
from gameboy_agent.terrain_navigation import cell, paths, steer_path, exits
from gameboy_agent.transitions import BUTTONS
from gameboy_agent.cave_navigation import plan_block_exit, block_changed
from gameboy_agent.progression_skills import dismiss_dialogue
from gameboy_agent.progression_contracts import settle_and_require_stage, adjacent_direction


def grid(boy):
    m = boy.memory
    start = 0x4AD4 + 256*int(m[0xDBA5]) + (256 if m[0xFFF7] == 255 else 0)
    flags = m[8, start:start+256]
    return [[int(flags[v]) for v in m[0xD711+r*16:0xD711+r*16+10]] for r in range(8)]


def execute(env, evidence, *, exchange=False, tarin=False, tail_key=False, tail_cave=False,
            route_controller=None):
    stage = 'tail-cave' if tail_cave else 'tail-key' if tail_key else 'tarin' if tarin else 'witch-exchange' if exchange else 'witch-approach'
    settle_and_require_stage(env,stage)
    began = env.total_steps

    def move(direction, frames=3):
        if env.total_steps-began >= 2048:
            raise RuntimeError('Witch approach exhausted 2048-decision extension budget')
        keys = [direction]
        state = snapshot(env.pyboy)
        if state['room'][0] == 0:
            if state['inventory'][0] == 4:
                keys.append('b')
            elif state['inventory'][1] == 4:
                keys.append('a')
        if state['room'] == [1,10,189] and state['inventory'][:2] == [4,1]:
            keys.append('b')
            m=env.pyboy.memory
            near=[i for i in range(16) if m[0xC280+i]==5 and m[0xC3A0+i]==25
                  and abs(int(m[0xC200+i])-state['x'])<=24
                  and abs(int(m[0xC210+i])-state['y'])<=24]
            if near:
                i=min(near,key=lambda i:abs(int(m[0xC200+i])-state['x'])+abs(int(m[0xC210+i])-state['y']))
                dx=int(m[0xC200+i])-state['x'];dy=int(m[0xC210+i])-state['y']
                aim=('right' if dx>=0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>=0 else 'up')
                face={'right':0,'left':1,'up':2,'down':3}[aim]
                keys=['b'] if m[0xC137] else [aim,'b'] if m[0xFF9E]!=face else ['a','b']
                frames=1
        env.step_buttons(keys, action_frames=frames)

    def approach(target, expected=None):
        origin = snapshot(env.pyboy)['room']
        previous, stationary, combat_attempts = None, 0, 0
        aimed_strikes = 0
        recent = []
        for _ in range(256):
            s = snapshot(env.pyboy)
            if s['dialog_state']:
                evidence.append(dict(kind='approach_dialogue', frame=env.frames,
                                     **dismiss_dialogue(env)))
                continue
            # Measured route bottlenecks: face a nearby sword-safe hostile before
            # swinging, instead of waiting until movement is pinned against it.
            # Buzz blobs are intentionally excluded because sword contact hurts.
            sword = 'a' if s['inventory'][1] == 1 else 'b' if s['inventory'][0] == 1 else None
            combat_rooms = (0x42, 0x52, 0x70, 0xE0)
            if s['room'][:2] == [0,0] and s['room'][2] in combat_rooms and sword and aimed_strikes < 32:
                m=env.pyboy.memory
                hostiles=[(int(m[0xC200+i])-s['x'],int(m[0xC210+i])-s['y'],i)
                          for i in range(16) if m[0xC280+i]==5 and m[0xC3A0+i] in (0x09,0x0B,0x14,0x1B,0x1C,0xC5)]
                near=[h for h in hostiles if abs(h[0])+abs(h[1]) <= 32]
                if near:
                    dx,dy,slot=min(near,key=lambda h:abs(h[0])+abs(h[1]))
                    facing=('right' if dx>0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>0 else 'up')
                    if m[0xC137]:
                        env.step_buttons([],action_frames=1)
                        continue
                    if m[0xFF9E]!={'right':0,'left':1,'up':2,'down':3}[facing]:
                        env.step_buttons([facing],action_frames=1)
                        continue
                    env.step_buttons([sword],action_frames=10)
                    env.step_buttons([],action_frames=3)
                    aimed_strikes += 1
                    evidence.append(dict(kind='aimed_sword_response',frame=env.frames,room=s['room'],
                                         entity_slot=slot,relative_position=[dx,dy],facing=facing))
                    continue
            route = paths(grid(env.pyboy), cell(s['x'], s['y']))
            if tuple(target) not in route:
                raise RuntimeError(f'No conservative path in {s["room"]} from '
                                   f'{cell(s["x"],s["y"])} to {target}; obstacle skill required')
            here = cell(s['x'], s['y'])
            waypoint = route[tuple(target)][0] if here != tuple(target) else target
            direction = steer_path(s['x'], s['y'], waypoint)
            if here == tuple(target) and direction is None:
                return
            if direction is None:
                continue
            move({1:'up',2:'down',3:'left',4:'right'}[direction])
            now = snapshot(env.pyboy)
            if now['room'] != origin:
                if now['room'] != expected:
                    raise RuntimeError(f'Unexpected approach transition: {origin} -> {now["room"]}')
                return
            position = (tuple(now['room']), now['x'], now['y'])
            stationary = stationary+1 if position == previous else 0
            previous = position
            recent.append(position[1:])
            recent = recent[-32:]
            pinned = (len(recent) == 32 and max(p[0] for p in recent)-min(p[0] for p in recent) <= 16
                      and max(p[1] for p in recent)-min(p[1] for p in recent) <= 16)
            if stationary >= 32 or pinned:
                # At most three short responses to observed shield-pinned movement.
                # Press the physically equipped sword; no enemy or inventory edits.
                sword = 'a' if now['inventory'][1] == 1 else 'b' if now['inventory'][0] == 1 else None
                if sword and combat_attempts < 3 and not now['dialog_state']:
                    combat_attempts += 1
                    forward = {1:'up',2:'down',3:'left',4:'right'}[direction]
                    for _ in range(4):
                        env.step_buttons([forward,sword],action_frames=10)
                        env.step_buttons([forward],action_frames=3)
                    evidence.append(dict(kind='bounded_sword_stall_response',room=now['room'],frame=env.frames))
                    stationary = 0
                    recent = []
                else:
                    raise RuntimeError(f'Physical approach stalled in {now["room"]} at {position[1:]}')
        raise RuntimeError(f'Approach budget exhausted at target {target}')

    def cross(direction, expected):
        old = snapshot(env.pyboy)['room']
        if old == expected:
            evidence.append(dict(kind='approach_transition_settled', target=expected, frame=env.frames))
            return
        for _ in range(128 if old == [1,10,189] else 64):
            current=snapshot(env.pyboy)
            crossing_direction=direction
            if old == [1,10,189] and expected == [0,0,98]:
                # Reobserve the doorway after combat/recoil instead of holding
                # down against the jamb from a displaced horizontal position.
                if current['x']<70:crossing_direction='right'
                elif current['x']>78:crossing_direction='left'
            move(crossing_direction)
            s = snapshot(env.pyboy)
            if s['room'] != old:
                if s['room'] != expected:
                    raise RuntimeError(f'Unexpected return transition: {old} -> {s["room"]}')
                evidence.append(dict(kind='return_transition', origin=old, target=expected, frame=env.frames))
                return
        raise RuntimeError(f'Entrance/crossing did not trigger from {old} toward {expected}')

    def traverse(rooms):
        for destination in rooms:
            current = snapshot(env.pyboy)
            if route_controller is not None and route_controller(env, evidence, destination):
                current = snapshot(env.pyboy)
                if current['room'] != [0,0,destination]:
                    raise RuntimeError(f'Route controller did not reach {destination:02X}: {current["room"]}')
                continue
            if tail_cave and current['room'] == [0,0,0xB0]:
                # Pass between the two children instead of centering on either.
                approach((6,2))
                approach((6,6))
                current = snapshot(env.pyboy)
            if tail_cave and current['room'] == [0,0,0x90]:
                # One bush blocks the narrow village approach beneath the entrance.
                approach((6,1))
                address = 0xD711 + 2*16 + 6
                if env.pyboy.memory[address] != 0x5C:
                    raise RuntimeError('Expected village-approach bush is absent')
                env.step_buttons(['down'],action_frames=3)
                for _ in range(4):
                    env.step_buttons(['down','a'],action_frames=10)
                    env.step_buttons([],action_frames=3)
                    if env.pyboy.memory[address] != 0x5C:
                        break
                if env.pyboy.memory[address] != 0x04:
                    raise RuntimeError('Village approach bush did not become ordinary floor')
                evidence.append(dict(kind='village_approach_bush_cut',frame=env.frames))
                current = snapshot(env.pyboy)
            direction,name = adjacent_direction(current['room'],destination)
            candidates = [e for e in exits(grid(env.pyboy),cell(current['x'],current['y']),
                          current['room'][2]) if e['direction']==direction]
            if not candidates:
                raise RuntimeError(f"No verified terrain path from {current['room']} toward {destination:02X}")
            # A corner can cross the perpendicular boundary during centering.
            # Prefer a non-corner exit when it is reachable.
            interior_edge = [e for e in candidates if not
                             (e['cell'][0] in (0,9) and e['cell'][1] in (0,7))]
            target = min(interior_edge or candidates,key=lambda e:len(e['path']))
            if tail_cave and current['room'] == [0,0,0xC3] and destination == 0xC2:
                # Re-enter C2's lower connected area via its east-side passage.
                target = next((e for e in candidates if tuple(e['cell']) == (0,5)), None)
                if target is None:
                    raise RuntimeError('Lower return passage into C2 is unreachable')
            approach(target['cell'], expected=[0,0,destination])
            cross(name,[0,0,destination])

    if tail_cave:
        env.step_input_events(release=BUTTONS, frames=1)
        traverse((0x51,0x61,0x60,0x70,0x80,0x90,0xA0,0xB0,0xC0,0xC1,0xC2,0xC3,0xC2,0xD2,0xD3))
        evidence.append(dict(kind='tail_cave_exterior_reached',frame=env.frames))
        # Source room D3 places the keyhole at (6,5) and entrance at (6,1).
        approach((6,6))
        for _ in range(24):
            env.step_buttons(['up'],action_frames=3)
            if snapshot(env.pyboy)['tail_door_status'] & 0x10:
                evidence.append(dict(kind='tail_keyhole_opened',frame=env.frames))
                break
        else:
            raise RuntimeError('Physical keyhole approach did not open Tail Cave')
        env.step_input_events(release=BUTTONS,frames=600)
        dismiss_dialogue(env)
        approach((6,2))
        cross('up',[1,0,0x17])
        if 'tail_cave_entered' not in env.journal.milestones:
            env.step_buttons([],action_frames=1)
        if 'tail_cave_entered' not in env.journal.milestones:
            raise RuntimeError('Tail Cave entry did not settle alive')
        evidence.append(dict(kind='tail_cave_entry_verified',frame=env.frames))
        return

    if tail_key:
        env.step_input_events(release=BUTTONS, frames=1)
        traverse((0x41,))
        # Source room 41 contains its Tail Key chest at column 4, row 3.
        chest_address = 0xD711 + 3*16 + 4
        if env.pyboy.memory[chest_address] != 0xA0:
            raise RuntimeError('Expected closed Tail Key chest is absent')
        # The chest's southern stance is occupied by a cuttable bush (5C).
        approach((4,5))
        from gameboy_agent.progression_skills import equip_item
        equip_item(env,1,button='a')
        bush_address = 0xD711 + 4*16 + 4
        bush_before = int(env.pyboy.memory[bush_address])
        if bush_before != 0x5C:
            raise RuntimeError('Expected chest-approach bush is absent')
        env.step_buttons(['up'], action_frames=3)
        for _ in range(4):
            env.step_buttons(['up','a'], action_frames=10)
            env.step_buttons([], action_frames=3)
            if env.pyboy.memory[bush_address] != bush_before:
                break
        if env.pyboy.memory[bush_address] == bush_before:
            raise RuntimeError('Physical sword input did not clear the chest-approach bush')
        evidence.append(dict(kind='chest_approach_bush_cut',frame=env.frames,
                             before=bush_before,after=int(env.pyboy.memory[bush_address])))
        approach((4,4))
        env.step_buttons(['up'], action_frames=6)
        for _ in range(12):
            env.step_input_events(['a'], release=[b for b in BUTTONS if b != 'a'], frames=1, release_after=['a'])
            env.step_input_events(frames=120)
            dismiss_dialogue(env)
            current = snapshot(env.pyboy)
            if current['tail_key']:
                env.step_input_events(frames=240)
                dismiss_dialogue(env)
                env.step_buttons([], action_frames=1)
                if env.pyboy.memory[chest_address] != 0xA1:
                    raise RuntimeError('Key possession appeared without the expected open chest')
                evidence.append(dict(kind='tail_key_chest_verified', frame=env.frames,
                                     room=current['room'], chest_cell=[4,3],
                                     chest_before=0xA0, chest_after=0xA1,
                                     tail_key=current['tail_key']))
                return
        raise RuntimeError('Chest interaction did not yield Tail Key within 12 pulses')

    if tarin:
        from gameboy_agent.progression_skills import equip_item
        equip_item(env,1,button='a')
        approach((4,6))
        cross('down',[0,0,0x65])
        traverse((0x64,0x54,0x44,0x43,0x42,0x52,0x62,0x61,0x51))
        evidence.append(dict(kind='tarin_room_reached',frame=env.frames))
        approach((7,5))
        equip_item(env,12,button='a')
        env.step_buttons(['up'],action_frames=3)
        initial_powder = snapshot(env.pyboy)['powder']
        for attempt in range(60):
            if attempt % 10 == 0:
                env.step_input_events(['a'],frames=1,release_after=['a'])
            env.step_input_events(frames=120)
            if snapshot(env.pyboy)['dialog_state']:
                dismiss_dialogue(env)
            current = snapshot(env.pyboy)
            if current['tarin'] == 1:
                env.step_input_events(frames=240)
                dismiss_dialogue(env)
                env.step_buttons([],action_frames=1)
                evidence.append(dict(kind='tarin_cure_verified',frame=env.frames,
                                     powder_before=initial_powder,powder_after=current['powder']))
                return
        raise RuntimeError('Physical powder interaction did not cure Tarin within the frame budget')

    if not exchange:
        # Release any pending controls before choosing the return approach.
        env.step_input_events(release=BUTTONS, frames=1)
        approach((8, 3))
        cross('up', [1, 10, 171])
        # At the bottom door, centering sideways hits the jamb. Clear the doorway
        # vertically before applying the ordinary room-cell centering controller.
        move('up', frames=16)
        # Re-entering reloads room grids; never assume earlier pushes persist.
        for direction, name, expected in ((4, 'right', [1, 10, 172]),
                                          (2, 'down', [1, 10, 189]),
                                          (2, 'down', [0, 0, 98])):
            current = snapshot(env.pyboy)
            candidates = [e for e in exits(grid(env.pyboy), cell(current['x'], current['y']),
                          current['room'][2]) if e['direction'] == direction]
            # The paired bottom doorway is a transition object (C1/C2), not normal
            # floor. Approach its interior stance, then require the actual warp.
            if current['room'] == [1,10,189] and expected == [0,0,98]:
                objects = env.pyboy.memory[0xD711:0xD791]
                route = paths(grid(env.pyboy),cell(current['x'],current['y'])).get((4,6))
                if objects[0x74:0x76] == [0xC1,0xC2] and route is not None:
                    candidates.append(dict(cell=[4,6],path=route))
            if not candidates:
                m = env.pyboy.memory
                offset = 0x4AD4 + 256*int(m[0xDBA5])
                plan = plan_block_exit(m[0xD711:0xD791], m[8,offset:offset+256],
                                       cell(current['x'],current['y']), direction=direction)
                evidence.append(dict(kind='return_block_plan', room=current['room'], **plan))
                if plan['status'] != 'planned':
                    raise RuntimeError(f"No conservative {name} return path in {current['room']}; "
                                       "obstacle/doorway skill required")
                for push in plan['pushes']:
                    approach(push['stance'])
                    before = list(m[0xD711:0xD791])
                    key = {1:'up',2:'down',3:'left',4:'right'}[push['direction']]
                    env.step_input_events([key], release=[b for b in BUTTONS if b != key],
                                          frames=96, release_after=[key])
                    env.step_input_events(frames=40)
                    after = list(m[0xD711:0xD791])
                    if (not block_changed(before,after,push)
                            or after[push['destination_index']] != 0xA6):
                        raise RuntimeError(f'Return push failed physical grid validation: {push}')
                    evidence.append(dict(kind='verified_return_push', **push, frame=env.frames))
                current = snapshot(env.pyboy)
                candidates = [e for e in exits(grid(env.pyboy), cell(current['x'],current['y']),
                               current['room'][2]) if e['direction'] == direction]
                if not candidates:
                    raise RuntimeError('Validated pushes did not open the intended return exit')
            target = min(candidates, key=lambda e:len(e['path']))
            approach(target['cell'], expected=expected)
            cross(name, expected)
        evidence.append(dict(kind='return_cave_complete', frame=env.frames))
        return

    # Supplied guide room order, verified against each actual transition.
    env.step_input_events(release=BUTTONS, frames=1)
    traverse((0x52,0x42,0x43,0x44,0x54,0x64,0x65))
    approach((4,3))
    cross('up',[1,14,162])
    evidence.append(dict(kind='witch_hut_entered',frame=env.frames))
    from gameboy_agent.progression_skills import equip_item
    equip_item(env,12,button='a')
    approach((4,5))
    env.step_buttons(['up'],action_frames=3)
    for _ in range(24):
        env.step_input_events(['a'],frames=1,release_after=['a'])
        env.step_input_events(frames=120)
        s = snapshot(env.pyboy)
        if not s['toadstool'] and s['powder']>0 and 12 in s['inventory']:
            dismiss_dialogue(env)
            env.step_buttons([],action_frames=1)
            evidence.append(dict(kind='witch_exchange_verified',frame=env.frames,powder=s['powder']))
            return
    raise RuntimeError('Witch interaction did not produce observed powder within 24 pulses')
