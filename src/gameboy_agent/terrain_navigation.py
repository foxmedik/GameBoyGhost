"""Conservative local grid navigation using privileged read-only room physics.

Only ordinary ground, shallow water, grass and stairs are admitted. Ledges,
unknown fine collision, removable obstacles and doors need separate skills.
"""
from collections import deque

PASSABLE=frozenset((0,2,5,6,10))
DIRECTIONS=((1,0,-1),(2,0,1),(3,-1,0),(4,1,0))


def terrain(boy):
    m=boy.memory
    if m[0xDBA5]!=0:raise ValueError('First terrain navigator supports overworld only')
    objects=[list(m[0xD711+r*16:0xD711+r*16+10]) for r in range(8)]
    flags=list(m[8,0x4AD4:0x4BD4])
    return [[flags[v] for v in row] for row in objects]


def cell(x,y):return (x//16,(y-4)//16)


def paths(grid,start):
    if not (0<=start[0]<10 and 0<=start[1]<8):return {}
    found={start:[]};queue=deque([start])
    while queue:
        here=queue.popleft()
        for _,dx,dy in DIRECTIONS:
            p=(here[0]+dx,here[1]+dy)
            if 0<=p[0]<10 and 0<=p[1]<8 and p not in found and grid[p[1]][p[0]] in PASSABLE:
                found[p]=found[here]+[p];queue.append(p)
    return found


def exits(grid,start,room):
    found=paths(grid,start);result=[]
    for p,path in found.items():
        if grid[p[1]][p[0]] not in PASSABLE:continue
        for direction,dx,dy in DIRECTIONS:
            if not (0<=p[0]+dx<10 and 0<=p[1]+dy<8):
                col,row=room%16+dx,room//16+dy
                if 0<=col<16 and 0<=row<16:
                    result.append(dict(direction=direction,cell=list(p),path=[list(c) for c in path],
                                       expected_room=row*16+col))
    return result


def component(grid,start):
    reachable=paths(grid,start)
    return min(reachable) if reachable else start


def choose_exit(grid,start,room,target,visits,rejected,known_grids=None):
    candidates=[e for e in exits(grid,start,room) if (room,e['direction'],tuple(e['cell'])) not in rejected]
    def score(e):
        r=e['expected_room']
        distance=abs(r%16-target%16)+abs(r//16-target//16)
        # Re-entering another connected area of a known room is useful discovery.
        if known_grids is None:
            count=visits.get(r,0)
        elif r not in known_grids:
            count=0
        else:
            x,y=e['cell'];landing=(x,7) if e['direction']==1 else (x,0) if e['direction']==2 else (9,y) if e['direction']==3 else (0,y)
            count=visits.get((r,component(known_grids[r],landing)),0)
        return (distance+4*count,len(e['path']),e['direction'],e['cell'])
    return min(candidates,key=score) if candidates else None


def steer(x,y,target):
    """Align to a cell centre; callers limit pulses to three frames."""
    tx,ty=target[0]*16+8,target[1]*16+12
    dx,dy=tx-x,ty-y
    if abs(dx)<=1 and abs(dy)<=1:return None
    # Centre laterally before walking up a narrow vertical corridor.
    return (4 if dx>0 else 3) if abs(dx)>1 else (2 if dy>0 else 1)


def steer_path(x, y, target):
    """Centre across a corridor before advancing to its adjacent path cell.

    A horizontal step must align Y first; a vertical step must align X first.
    This avoids cutting a solid corner when replanning after displacement.
    """
    here = cell(x, y)
    tx, ty = target[0]*16+8, target[1]*16+12
    if target[0] != here[0] and target[1] == here[1]:
        if abs(ty-y) > 4:
            return 2 if ty > y else 1
        return 4 if tx > x else 3
    if target[1] != here[1] and target[0] == here[0]:
        if abs(tx-x) > 4:
            return 4 if tx > x else 3
        return 2 if ty > y else 1
    return steer(x, y, target)
