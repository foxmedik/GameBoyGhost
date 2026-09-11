"""Teacher-only LADX 1.1 terrain gate. See docs/PROXIMITY_SWORD_48_V2.md."""
from proximity_sword import THREATS, inputs as proximity_inputs

# bank0.asm 158F-15A6, after subtracting the hardware coordinate offsets.
SWORD_OFFSETS = ((14, -8), (-14, -8), (0, -22), (0, 6))
MOVEMENT_FACING = {4: 0, 3: 1, 1: 2, 2: 3}
MOVEMENT_VECTOR = {0: (0, 0), 1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}
CUTTABLE = {False: frozenset((0x0A, 0x5C, 0xD3)), True: frozenset((0xDD,))}


def signed(byte):
    return byte if byte < 128 else byte - 256


def reachable_terrain(*, x, y, facing, movement, indoor, objects, physics,
                      cutting_blocked=False):
    """Tile hit by an ordinary swing facing the requested movement.

    UseSword calls func_157C, which turns Link to the held d-pad direction.
    Room objects have 16-byte row stride, ten visible columns, eight rows.
    No spin/beam/boots prediction and no adjacent-room or remembered map access.
    """
    if movement not in MOVEMENT_FACING or cutting_blocked:
        return None
    facing = MOVEMENT_FACING.get(movement, facing)
    dx, dy = SWORD_OFFSETS[facing]
    col, row = (x + dx) // 16, (y + dy) // 16
    if not (0 <= col < 10 and 0 <= row < 8):
        return None
    index = row * 16 + col
    obj = objects[index]
    flags = physics[obj]
    if obj in CUTTABLE[bool(indoor)] and flags < 0x90 and flags != 1:
        return dict(index=index, row=row, col=col, object_id=obj, physics=flags,
                    facing=facing, sample_x=x + dx, sample_y=y + dy)
    return None


def exit_uncertain(x, y, movement):
    # Deliberately conservative 24-pixel guard around the visible room edges.
    # A ten-ready-frame action may traverse a loading wait into an unseen room.
    return ((movement == 3 and x <= 24) or (movement == 4 and x >= 136)
            or (movement == 1 and y <= 40) or (movement == 2 and y >= 120))


def approaching(entities, x, y, movement, horizon=20, radius=32):
    """Closest linear approach until the next cadence opportunity (20 frames).

    Entity signed RAM speed is pixels/16 frames. Evaluate stationary Link and
    a nominal 1 pixel/frame intended movement; obstacles can stop Link. This
    is a hypothesis, not a guarantee against acceleration or room transitions.
    """
    for e in entities:
        if not e['status'] or e['type'] not in THREATS:
            continue
        rx, ry = e['x'] - x, e['y'] - y
        for lx, ly in ((0, 0), MOVEMENT_VECTOR[movement]):
            vx, vy = e['vx'] - lx, e['vy'] - ly
            speed2 = vx * vx + vy * vy
            t = max(0, min(horizon, -(rx * vx + ry * vy) / speed2)) if speed2 else 0
            if (rx + vx * t)**2 + (ry + vy * t)**2 <= radius**2:
                return True
    return False


def gate(action, *, dialogue, sword_button, sword_state, entities, x, y,
         facing, indoor, objects, physics, cutting_blocked=False, motion=False):
    action = list(action)
    if dialogue or not sword_button or action[1] != sword_button:
        return action, 'unchanged'
    if sword_state in (1, 2, 3, 4):
        return [action[0], 0], 'swing_active'
    if any(e['status'] and e['type'] in THREATS and
           (e['x']-x)**2 + (e['y']-y)**2 <= 32**2 for e in entities):
        return action, 'near_threat'
    if reachable_terrain(x=x, y=y, facing=facing, movement=action[0], indoor=indoor,
                         objects=objects, physics=physics, cutting_blocked=cutting_blocked):
        return action, 'reachable_foliage'
    if exit_uncertain(x, y, action[0]):
        return action, 'unseen_exit'
    if motion and approaching(entities, x, y, action[0]):
        return action, 'closing_threat'
    return [action[0], 0], 'clear_path'


def inputs(base):
    m = base.pyboy.memory
    info = proximity_inputs(base)
    for e in info['entities']:
        i = e['slot']
        e.update(vx=signed(int(m[0xC240+i])) / 16, vy=signed(int(m[0xC250+i])) / 16)
    indoor = int(m[0xDBA5])
    # GetObjectPhysicsFlags: bank 8, 4AD4 + map group*256; color map adds 256.
    start = 0x4AD4 + 256 * indoor + (256 if m[0xFFF7] == 0xFF else 0)
    info.update(facing=int(m[0xFF9E]), indoor=indoor,
                objects=list(m[0xD711:0xD791]),
                physics=list(m[8, start:start+256]),
                cutting_blocked=bool(m[0xC1C4] or (not m[0xC14A] and m[0xC16A] == 5)))
    return info
