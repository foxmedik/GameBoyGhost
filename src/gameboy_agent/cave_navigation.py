"""Read-only cave transition and pushable-block senses for progression work.

These helpers never alter emulator RAM.  They expose only loaded warp records
and the ROM-designated indoor pushable-block object, not a visual guess that a
rock might move.
"""

PUSHABLE_BLOCK = 0xA7
SWORD_BREAKABLE_CRYSTAL = 0xDD
PUSH_FRAMES = 64
ROOM_STRIDE = 16
VISIBLE_COLUMNS = 10
VISIBLE_ROWS = 8

# Verified from the user's annotated route and physical object-grid changes in
# the mushroom cave's stone room (IndoorsAAB).  These are world facts for this
# one room, rather than a rule inferred from the appearance of every rock.
TOADSTOOL_STONE_ROOM = (1, 0x0A, 0xAB)
TOADSTOOL_STONE_PUSHES = (
    dict(index=0x37, col=7, row=3, direction=3),  # push left
    dict(index=0x57, col=7, row=5, direction=2),  # then push down
)


def loaded_warps(boy):
    """Return populated room warp records, including their trigger tile."""
    memory = boy.memory
    result = []
    for index in range(4):
        offset = 0xD401 + index * 5
        category, map_id, room, x, y = (int(v) for v in memory[offset:offset + 5])
        tile = int(memory[0xD416 + index])
        # The four slots are not cleared uniformly when a room changes.  A
        # category outside the three map categories is therefore stale data,
        # rather than a transition the planner may follow.
        if category not in (0, 1, 2):
            continue
        if (category, map_id, room, x, y, tile) == (0, 0, 0, 0, 0, 0):
            continue
        result.append(dict(index=index, category=category, map=map_id, room=room,
                           destination_x=x, destination_y=y, tile_index=tile,
                           col=tile & 0x0F, row=tile >> 4))
    return result


def pushable_blocks(boy):
    """Return visible indoor ``OBJECT_PUSHABLE_BLOCK`` cells only."""
    if int(boy.memory[0xDBA5]) == 0:
        return []
    objects = boy.memory[0xD711:0xD791]
    return [dict(index=index, col=index % ROOM_STRIDE, row=index // ROOM_STRIDE,
                 object_id=PUSHABLE_BLOCK)
            for index, value in enumerate(objects)
            if int(value) == PUSHABLE_BLOCK
            and index % ROOM_STRIDE < VISIBLE_COLUMNS
            and index // ROOM_STRIDE < VISIBLE_ROWS]


def breakable_crystals(boy):
    """Return visible cave crystals that must be cleared before block routing.

    ``OBJECT_SWORD_BLOCK`` is ``DD`` in the matched ROM.  The object is only
    a candidate until a physical sword swing changes its room-object entry.
    """
    if int(boy.memory[0xDBA5]) == 0:
        return []
    objects = boy.memory[0xD711:0xD791]
    return [dict(index=index, col=index % ROOM_STRIDE, row=index // ROOM_STRIDE,
                 object_id=SWORD_BREAKABLE_CRYSTAL)
            for index, value in enumerate(objects)
            if int(value) == SWORD_BREAKABLE_CRYSTAL
            and index % ROOM_STRIDE < VISIBLE_COLUMNS
            and index // ROOM_STRIDE < VISIBLE_ROWS]


def push_direction(link_cell, block_cell):
    """D-pad direction needed when Link is adjacent to a pushable block.

    The result uses the project's movement encoding: up=1, down=2, left=3,
    right=4.  Diagonal and non-adjacent positions deliberately return ``None``.
    """
    dx, dy = block_cell[0] - link_cell[0], block_cell[1] - link_cell[1]
    return {(0, -1): 1, (0, 1): 2, (-1, 0): 3, (1, 0): 4}.get((dx, dy))


def block_changed(before, after, block):
    """Whether the original block cell changed after a physical push attempt."""
    index = int(block['index'])
    return int(before[index]) == PUSHABLE_BLOCK and int(after[index]) != PUSHABLE_BLOCK


def crystal_cleared(before, after, crystal):
    """Whether a physical sword action removed the selected crystal tile."""
    index = int(crystal['index'])
    return (int(before[index]) == SWORD_BREAKABLE_CRYSTAL
            and int(after[index]) != SWORD_BREAKABLE_CRYSTAL)


def obstacle_phase(boy):
    """Return the required local cave interaction phase.

    Crystal gates are resolved first because they can be the only obstruction
    between Link and the stance needed for a block push.  The result describes
    the current room only; it does not infer that every crystal must be broken.
    """
    crystals = breakable_crystals(boy)
    if crystals:
        return dict(kind='clear_crystals', targets=crystals)
    blocks = pushable_blocks(boy)
    if blocks:
        return dict(kind='push_blocks', targets=blocks)
    return dict(kind='navigate', targets=[])


def toadstool_stone_push_plan(boy):
    """Return the verified two-push plan when the loaded room is IndoorsAAB.

    A plan is emitted only while both original blocks are still present.  Each
    completed push must be observed through :func:`block_changed` before the
    caller advances to the next entry or follows the exit walk.
    """
    memory = boy.memory
    location = (int(memory[0xDBA5]), int(memory[0xFFF7]), int(memory[0xFFF6]))
    if location != TOADSTOOL_STONE_ROOM:
        return []
    objects = memory[0xD711:0xD791]
    return [dict(push) for push in TOADSTOOL_STONE_PUSHES
            if int(objects[push['index']]) == PUSHABLE_BLOCK]


def plan_block_exit(objects, physics, start, *, direction=4, max_states=4096):
    """Bounded room-local search, treating a pushed block as immovable A6.

    The matched 03_pushed_block handler installs A6 after the move. Only A7
    may be pushed, only into ordinary traversable floor, with a reachable stance.
    This is a geometry hypothesis; callers must verify every physical grid change.
    """
    from collections import deque
    from gameboy_agent.terrain_navigation import PASSABLE, paths, DIRECTIONS
    initial = tuple(int(v) for v in objects)
    queue = deque([(initial, tuple(start), [])])
    visited = set()
    while queue and len(visited) < max_states:
        cells, player, plan = queue.popleft()
        grid = [[physics[cells[y*16+x]] for x in range(10)] for y in range(8)]
        reachable = paths(grid, player)
        key = (cells, min(reachable) if reachable else player)
        if key in visited:
            continue
        visited.add(key)
        edge = lambda p: (p[0] == 9 if direction == 4 else p[0] == 0 if direction == 3
                          else p[1] == 0 if direction == 1 else p[1] == 7)
        if any(edge(p) and grid[p[1]][p[0]] in PASSABLE for p in reachable):
            return dict(status='planned', pushes=plan, states=len(visited))
        for index, value in enumerate(cells):
            x, y = index % 16, index // 16
            if value != PUSHABLE_BLOCK or not (0 <= x < 10 and 0 <= y < 8):
                continue
            for movement, dx, dy in DIRECTIONS:
                stance, destination = (x-dx,y-dy), (x+dx,y+dy)
                tx, ty = destination
                if (stance not in reachable or not (0 <= tx < 10 and 0 <= ty < 8)
                        or grid[ty][tx] not in PASSABLE):
                    continue
                changed = list(cells)
                changed[index], changed[ty*16+tx] = 0x0D, 0xA6
                push = dict(index=index, direction=movement, stance=list(stance),
                            destination_index=ty*16+tx)
                queue.append((tuple(changed), (x,y), plan+[push]))
    return dict(status='no_plan_within_budget', pushes=[], states=len(visited))
