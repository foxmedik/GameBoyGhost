"""State-driven dungeon item development; unqualified for learner labels."""
from gameboy_agent.nightmare_key_route import RouteBlocker
from gameboy_agent.progression import snapshot, mode
from gameboy_agent.progression_skills import dismiss_dialogue


class ItemSteps:
    def __init__(self, env):
        self.env = env
        self.health = snapshot(env.pyboy)['health']
        self.last_swing = -100

    def check(self, room, dialog_ids=()):
        s = snapshot(self.env.pyboy)
        m = self.env.pyboy.memory
        if s['room'] != [1, 0, room] or not s['health'] or s['health'] < self.health:
            raise RouteBlocker('Item route room or health interruption')
        if m[0xDB94] or m[0xC11C] == 6:
            raise RouteBlocker('Item route buffered damage or falling')
        if s['dialog_state']:
            if s['dialog_id'] not in dialog_ids:
                raise RouteBlocker(f'Unexpected item-route dialogue {s["dialog_id"]:03X}')
        elif mode(s) != 'world':
            raise RouteBlocker('Item route is not playable')
        return s

    def ready(self,room):
        for _ in range(4):
            s=self.check(room,(8,0xEC))
            m=self.env.pyboy.memory
            if m[0xC1A9] and not s['dialog_state']:
                if m[0xC1A9] not in (1,5):
                    raise RouteBlocker('Unexpected pending item receipt')
                for _ in range(60):
                    self.env.step_buttons([],action_frames=1)
                    s=self.check(room,(8,0xEC))
                    if s['dialog_state']:break
                else:raise RouteBlocker('Pending power-up receipt did not appear')
            if s['dialog_state']:
                dismiss_dialogue(self.env)
                continue
            return s
        raise RouteBlocker('Power-up receipts did not settle')

    def move(self, room, direction, done, budget=180, defend=False):
        stagnant = 0
        for _ in range(budget):
            s = self.ready(room)
            if done(s):
                self.env.step_buttons([], action_frames=1)
                return self.ready(room)
            buttons = [direction, 'b']
            m = self.env.pyboy.memory
            targets = [i for i in range(16) if m[0xC280+i]==5 and m[0xC3A0+i] in (25, 28, 30, 32)
                       and abs(int(m[0xC200+i])-s['x']) <= 28
                       and abs(int(m[0xC210+i])-s['y']) <= 28] if defend else []
            if targets and not m[0xC137] and self.env.frames-self.last_swing >= 24:
                i = min(targets, key=lambda i: abs(int(m[0xC200+i])-s['x'])
                        + abs(int(m[0xC210+i])-s['y']))
                z = int(m[0xC310+i]) if m[0xC3A0+i] == 28 else 0
                dx, dy = int(m[0xC200+i])-s['x'], int(m[0xC210+i])-z-s['y']
                face = ('right' if dx >= 0 else 'left') if abs(dx) > abs(dy) else ('down' if dy >= 0 else 'up')
                reach=18 if m[0xC3A0+i]==28 else 28
                if abs(dx)<=reach and abs(dy)<=reach:
                    buttons=[face,'b']
                    if m[0xFF9E]=={'right':0,'left':1,'up':2,'down':3}[face]:
                        buttons.append('a')
                        self.last_swing=self.env.frames
            self.env.step_buttons(buttons, action_frames=1)
            new = self.check(room, (8, 0xEC))
            stagnant = stagnant+1 if (new['x'], new['y']) == (s['x'], s['y']) and 'a' not in buttons else 0
            if stagnant >= 24 and not new['dialog_state']:
                raise RouteBlocker(f'Item route blocked {direction} at {(new["x"], new["y"])}')
        raise RouteBlocker('Item movement budget exhausted')

    def travel(self, room, direction, dest, budget=180):
        self.ready(room)
        for _ in range(budget):
            self.env.step_buttons([direction, 'b'], action_frames=1)
            s = snapshot(self.env.pyboy)
            if s['room'] == [1, 0, dest]:
                return self.ready(dest)
            self.ready(room)
        raise RouteBlocker('Item room transition budget exhausted')

    def chest(self, room, address, expected, dialog_id):
        self.check(room)
        m = self.env.pyboy.memory
        if m[address] == expected:
            raise RouteBlocker('Chest target already owned; acquisition not fresh')
        self.env.step_buttons(['up', 'a'], action_frames=1)
        for _ in range(180):
            s = self.check(room, (dialog_id,))
            if s['dialog_state']:
                break
            self.env.step_buttons([], action_frames=1)
        else:
            raise RouteBlocker('Chest receipt did not appear')
        if m[address] != expected:
            raise RouteBlocker('Chest did not grant the expected item/count')
        dismiss_dialogue(self.env)
        self.check(room)


def compass_and_second_key(env, evidence):
    r = ItemSteps(env)
    r.check(21, (8, 0xEC))
    m = env.pyboy.memory
    if m[0xDBCD] or m[0xDBD0] != 1 or list(m[0xDB00:0xDB02]) != [4, 1]:
        raise RouteBlocker('Compass stage requires shield B, sword A, one key and no Compass')
    if any(m[0xC280+i] and m[0xC3A0+i] in (0x9B, 0x7D) for i in range(16)):
        raise RouteBlocker('Room15 combat/projectiles must be cleared before item stage')
    r.move(21, 'down' if snapshot(env.pyboy)['y'] < 88 else 'up', lambda s: s['y'] == 88)
    r.move(21, 'left', lambda s: s['x'] <= 38)
    r.move(21, 'up', lambda s: s['y'] <= 71)
    r.move(21, 'right', lambda s: s['x'] >= 56)
    r.chest(21, 0xDBCD, 1, 0xA7)
    evidence.append(dict(kind='compass_received', frame=env.frames, state=snapshot(env.pyboy)))
    r.travel(21, 'right', 22)
    reclear_hardhat_return(env,evidence)
    r.move(22,'down' if snapshot(env.pyboy)['y']<71 else 'up',lambda s:70<=s['y']<=72)
    r.travel(22, 'right', 23)
    r.move(23, 'right', lambda s: s['x'] >= 26)
    r.move(23, 'down', lambda s: s['y'] >= 92)
    r.move(23, 'right', lambda s: s['x'] >= 80)
    r.travel(23, 'up', 19)
    r.move(19, 'up', lambda s: s['y'] <= 109, defend=True)
    r.move(19, 'left', lambda s: s['x'] <= 37, defend=True)
    r.move(19, 'up', lambda s: s['y'] <= 26, defend=True)
    r.move(19, 'right', lambda s: s['x'] >= 88, defend=True, budget=300)
    r.move(19, 'down', lambda s: s['y'] >= 64, defend=True)
    for _ in range(60):
        r.check(19)
        if m[0xD711+0x28] == 0xA0 and m[0xC18F]:break
        env.step_buttons(['b'],action_frames=1)
    else:raise RouteBlocker('Floor switch did not resolve its event and spawn the chest')
    r.move(19, 'up', lambda s: s['y'] <= 26, defend=True)
    r.move(19, 'right', lambda s: s['x'] >= 120, defend=True)
    r.move(19, 'down', lambda s: s['y'] >= 64, defend=True)
    r.move(19, 'right', lambda s: s['x'] >= 136, defend=True)
    r.move(19, 'up', lambda s: s['y'] <= 58, defend=True)
    r.chest(19, 0xDBD0, 2, 0xAA)
    if m[0xDBCD] != 1:
        raise RouteBlocker('Compass disappeared during second key stage')
    evidence.append(dict(kind='second_key_received', frame=env.frames, state=snapshot(env.pyboy)))


def acquire_map(env, evidence):
    r = ItemSteps(env)
    r.check(19)
    m = env.pyboy.memory
    if m[0xDBCC] or m[0xDBCD] != 1 or m[0xDBD0] != 2 or list(m[0xDB00:0xDB02]) != [4, 1]:
        raise RouteBlocker('Map stage requires shield B, sword A, Compass, two keys, no Map')
    r.move(19, 'down', lambda s: s['y'] >= 72)
    r.travel(19, 'right', 20)
    r.move(20, 'right', lambda s: s['x'] >= 32, defend=True)
    r.move(20, 'down', lambda s: s['y'] >= 110, defend=True)
    clear_map_enemies(env, evidence, budget=900)
    for _ in range(90):
        r.ready(20)
        chests=[index for index in range(128) if m[0xD711+index]==0xA0]
        if len(chests)==1 and chests[0] in (0x28,0x38):break
        if chests:raise RouteBlocker('Unexpected closed Map chest tile')
        env.step_buttons([],action_frames=1)
    else:raise RouteBlocker('Map closed chest did not appear within90 frames')
    chest_y=(chests[0]//16)*16+26
    evidence.append(dict(kind='map_chest_observed',frame=env.frames,tile_index=chests[0],approach_y=chest_y))
    # Enter a clear vertical aisle before descending past the statues.
    x=snapshot(env.pyboy)['x'];lane=min((40,80,120),key=lambda v:abs(v-x))
    r.move(20,'left' if x>lane else 'right',
           (lambda s:s['x']<=lane) if x>lane else (lambda s:s['x']>=lane))
    r.move(20, 'down', lambda s: s['y'] >= 110, defend=True)
    r.move(20, 'right', lambda s: s['x'] >= 136, defend=True)
    r.move(20, 'up', lambda s: s['y'] <= chest_y, defend=True)
    r.chest(20, 0xDBCC, 1, 0xA6)
    evidence.append(dict(kind='map_received', frame=env.frames, state=snapshot(env.pyboy)))


def clear_map_enemies(env, evidence, budget=600, room=20, kinds=(25, 30)):
    r = ItemSteps(env)
    last_swing = -32
    stagnant=0;detour=[]
    for index in range(budget):
        s = r.check(room, (8, 0xEC))
        m = env.pyboy.memory
        if s['dialog_state']:
            dismiss_dialogue(env,precise=True)
            continue
        occupied = [i for i in range(16) if m[0xC280+i] and m[0xC3A0+i] in kinds]
        targets = [i for i in occupied if m[0xC280+i]==5]
        if not occupied:
            env.step_buttons([], action_frames=1)
            r.check(room)
            return
        if not targets:
            env.step_buttons([],action_frames=1)
            continue
        i = min(targets, key=lambda i: abs(int(m[0xC200+i])-s['x']) + abs(int(m[0xC210+i])-s['y']))
        dx = int(m[0xC200+i])-s['x']
        dy = int(m[0xC210+i])-int(m[0xC310+i])-s['y']
        direction = ('right' if dx >= 0 else 'left') if abs(dx)>abs(dy) else ('down' if dy >= 0 else 'up')
        facing = dict(right=0, left=1, up=2, down=3)[direction]
        # Evasive Stalfos retreat when either action button is held nearby.
        # Approach without the shield, then strike only after facing is set.
        evasive = m[0xC3A0+i] == 30
        buttons = [] if evasive else ['b']
        reach = 18 if evasive else 28
        chase = abs(dx)+abs(dy)>reach and not (room==7 and direction=='up' and s['y']<=94)
        if chase or m[0xFF9E] != facing:
            buttons.append(direction)
        if (abs(dx)<=reach and abs(dy)<=reach and m[0xFF9E] == facing
                and env.frames-last_swing>=24):
            buttons.append('a')
            last_swing=env.frames
        if (evasive and abs(dx)<=18 and abs(int(m[0xC210+i])-s['y'])<=18
                and (m[0xFF9E]!=facing or env.frames-last_swing<24) and 'a' not in buttons):
            # Turn the shield toward contact while waiting for a sword swing.
            # Holding B without the turn leaves the previous flank exposed.
            buttons=['b']+([direction] if m[0xFF9E]!=facing else [])
        if stagnant>=12 and room==20:
            # Floor0F is passable. Only the two torches/statues interrupt
            # pursuit; row64 connects the three clear vertical aisles.
            lane=40 if m[0xC200+i]<64 else (120 if m[0xC200+i]>96 else 80)
            target_y=max(32,min(110,int(m[0xC210+i])))
            entry_lane=min((40,80,120),key=lambda v:abs(v-s['x']))
            detour=[('left' if s['x']>entry_lane else 'right',entry_lane),
                    ('up' if s['y']>64 else 'down',64),
                    ('left' if entry_lane>lane else 'right',lane),
                    ('up' if target_y<64 else 'down',target_y)]
            stagnant=0
        if detour and abs(dx)<=reach and abs(dy)<=reach:
            detour=[]
        while detour:
            direction,target=detour[0]
            value=s['y'] if direction in ('up','down') else s['x']
            done=value<=target if direction in ('left','up') else value>=target
            if done:detour.pop(0)
            else:break
        if detour:buttons=[detour[0][0]]
        if room==20 and s['x']<=40:
            # Keep sword recoil away from the west-side pits.
            if 'left' in buttons:buttons.remove('left')
            if s['x']<40:buttons=['right','b']
        env.step_buttons(buttons, action_frames=1)
        after=snapshot(env.pyboy)
        walking=any(v in buttons for v in ('up','down','left','right'))
        stagnant=(stagnant+1 if walking and not m[0xC137]
                  and (s['x'],s['y'])==(after['x'],after['y']) else 0)
    raise RouteBlocker('Map enemy clearance budget exhausted')


def reach_south_worm_entry(env, evidence):
    r=ItemSteps(env)
    r.check(20)
    m=env.pyboy.memory
    if list(m[0xDBCC:0xDBCE]) != [1,1] or m[0xDBD0] != 2:
        raise RouteBlocker('Onward entry requires Map, Compass and two keys')
    r.move(20, 'down', lambda s:s['y']>=74, defend=True)
    r.travel(20, 'left', 19)
    r.move(19, 'left', lambda s:s['x']<=122, defend=True)
    r.move(19, 'down', lambda s:s['y']>=101, defend=True)
    r.move(19, 'left', lambda s:s['x']<=36, defend=True)
    r.move(19, 'up', lambda s:s['y']<=68, defend=True)
    r.travel(19, 'left', 18)
    r.move(18, 'left', lambda s:s['x']<=116, defend=True)
    r.move(18, 'up', lambda s:s['y']<=43, defend=True)
    r.move(18, 'left', lambda s:s['x']<=80, defend=True)
    clear_map_enemies(env, evidence, room=18, kinds=(25,))
    r.travel(18, 'up', 13)
    evidence.append(dict(kind='south_worm_entry',frame=env.frames,state=snapshot(env.pyboy)))


def cross_south_worm_room(env, evidence):
    r=ItemSteps(env)
    s=r.check(13)
    m=env.pyboy.memory
    if not (68 <= s['x'] <= 84 and s['y'] >= 120) or m[0xDBD0] != 2 or list(m[0xDB00:0xDB02]) != [4,1]:
        raise RouteBlocker('South worm route requires south entry, two keys, shield B and sword A')
    r.move(13, 'up', lambda s:s['y']<=122)
    env.step_buttons(['up','a'],action_frames=8)
    r.check(13)
    r.move(13, 'up', lambda s:s['y']<=89)
    if m[0xDBD0] != 2:
        raise RouteBlocker('Cuttable barrier unexpectedly spent a key')
    last_swing=-32
    for index in range(180):
        s=snapshot(env.pyboy)
        if s['room']==[1,0,7]:
            r.check(7)
            break
        r.check(13)
        worms=[i for i in range(16) if m[0xC280+i]==5 and m[0xC3A0+i]==41]
        i=worms[0] if worms else None
        dx=int(m[0xC200+i])-s['x'] if i is not None else 999
        dy=int(m[0xC210+i])-s['y'] if i is not None else 999
        direction=('left' if s['x']>80 else 'right') if s['y']<=60 and not 76<=s['x']<=80 else 'up'
        buttons=[direction,'b']
        if abs(dx)<=24 and abs(dy)<=24 and abs(dx)>abs(dy):
            side='right' if dx>0 else 'left'
            buttons=['b']+([side] if m[0xFF9E]!=(0 if dx>0 else 1) else [])
        elif (abs(dx)<=10 and -24<=dy<=4 and direction=='up' and m[0xFF9E]==2
              and not m[0xC137] and env.frames-last_swing>=24):
            buttons.append('a');last_swing=env.frames
        env.step_buttons(buttons,action_frames=1)
    else:
        raise RouteBlocker('Southern worm passage budget exhausted')
    if m[0xDBD0] != 2:
        raise RouteBlocker('Southern worm exit inventory mismatch')
    evidence.append(dict(kind='south_worm_passage',frame=env.frames,state=snapshot(env.pyboy)))


def reach_pushblock_room(env,evidence):
    r=ItemSteps(env)
    r.check(7)
    m=env.pyboy.memory
    if m[0xDBD0]!=2 or list(m[0xDB00:0xDB02]) != [4,1]:
        raise RouteBlocker('Room07 requires two keys, shield B and sword A')
    r.move(7,'up',lambda s:s['y']<=103,defend=True)
    clear_map_enemies(env,evidence,room=7,kinds=(25,))
    r.move(7,'down' if snapshot(env.pyboy)['y']<92 else 'up',lambda s:90<=s['y']<=92)
    r.move(7,'left',lambda s:s['x']<=70)
    traps=[i for i in range(16) if m[0xC280+i] and m[0xC3A0+i]==39]
    if len(traps)!=1:raise RouteBlocker('Room07 requires one observed spike trap')
    trap=traps[0]
    for _ in range(240):
        r.check(7)
        if m[0xC290+trap]==1 and m[0xC2E0+trap]==0:break
        env.step_buttons([],action_frames=1)
    else:raise RouteBlocker('Room07 trap did not become ready for bait')
    for _ in range(24):
        r.check(7)
        if m[0xC290+trap]==2:break
        env.step_buttons(['up'],action_frames=1)
    else:raise RouteBlocker('Room07 trap bait did not charge')
    r.move(7,'down',lambda s:s['y']>=92)
    for _ in range(220):
        r.check(7)
        if m[0xC290+trap]==3 and m[0xC200+trap]<=48:break
        env.step_buttons([],action_frames=1)
    else:raise RouteBlocker('Room07 trap did not retreat clear of crossing')
    evidence.append(dict(kind='room07_trap_crossing_clear',frame=env.frames,
                         trap_x=int(m[0xC200+trap]),trap_state=int(m[0xC290+trap])))
    r.move(7,'up',lambda s:s['y']<=40)
    r.move(7,'right',lambda s:s['x']>=79)
    r.travel(7,'up',4)
    if m[0xDBD0]!=1:
        raise RouteBlocker('Room07 north lock did not spend exactly one key')
    evidence.append(dict(kind='pushblock_room_entry',frame=env.frames,state=snapshot(env.pyboy)))


def solve_pushblock_room(env,evidence):
    r=ItemSteps(env)
    s=r.check(4)
    m=env.pyboy.memory
    if s['y']<120 or m[0xDBD0]!=1:
        raise RouteBlocker('Pushblock stage requires south entrance and one key')
    r.move(4,'up',lambda s:s['y']<=112)
    r.move(4,'right',lambda s:s['x']>=148)
    detour_room05(env,evidence)
    r.move(4,'down',lambda s:s['y']>=80)
    for _ in range(180):
        r.check(4)
        sparks=[i for i in range(16) if m[0xC280+i] and m[0xC3A0+i]==23]
        if len(sparks)!=1:raise RouteBlocker('Expected one pushblock room Spark')
        i=sparks[0]
        if m[0xC200+i]>=100 and m[0xC210+i]<=40:
            break
        env.step_buttons([],action_frames=1)
    else:raise RouteBlocker('Spark clearance window did not arrive')
    r.move(4,'left',lambda s:s['x']<=24)
    r.move(4,'up',lambda s:s['y']<=64)
    for _ in range(80):
        s=r.check(4)
        if s['x']>=40 and m[0xD711+0x32]!=0xA7:
            break
        env.step_buttons(['right'],action_frames=1)
    else:raise RouteBlocker('Pushblock did not move within budget')
    r.move(4,'up',lambda s:s['y']<=48)
    r.travel(4,'left',3)
    if m[0xDBD0]!=1:raise RouteBlocker('Pushblock exit inventory mismatch')
    evidence.append(dict(kind='pushblock_solved',frame=env.frames,state=snapshot(env.pyboy)))


def detour_room05(env,evidence):
    r=ItemSteps(env)
    r.check(4)
    r.move(4,'up',lambda s:s['y']<=98)
    r.travel(4,'right',5)
    r.move(5,'down',lambda s:s['y']>=112,defend=True)
    r.move(5,'right',lambda s:s['x']>=124,defend=True)
    r.move(5,'up',lambda s:s['y']<=98,defend=True)
    r.move(5,'right',lambda s:s['x']>=136,defend=True)
    r.move(5,'up',lambda s:s['y']<=48,defend=True)
    r.move(5,'left',lambda s:s['x']<=120,defend=True)
    r.move(5,'up',lambda s:s['y']<=27,defend=True)
    r.move(5,'left',lambda s:s['x']<=88,defend=True)
    wait_left_spark(env, lambda x,y,vx,vy:x>=60 and y>=50 and 0<vy<128)
    r.move(5,'left',lambda s:s['x']<=20,defend=True)
    wait_left_spark(env, lambda x,y,vx,vy:x>=53 and y<=40 and 0<vx<128)
    r.move(5,'down',lambda s:s['y']>=65)
    r.travel(5,'left',4)
    evidence.append(dict(kind='room05_detour',frame=env.frames,state=snapshot(env.pyboy)))


def wait_left_spark(env, clear):
    r=ItemSteps(env)
    m=env.pyboy.memory
    for _ in range(180):
        r.check(5)
        sparks=[i for i in range(16) if m[0xC280+i] and m[0xC3A0+i]==23]
        if len(sparks)!=1:raise RouteBlocker('Expected one left room05 Spark')
        i=sparks[0]
        if clear(m[0xC200+i],m[0xC210+i],m[0xC240+i],m[0xC250+i]):return
        env.step_buttons([],action_frames=1)
    raise RouteBlocker('Room05 Spark clearance budget exhausted')


def spiked_beetles_to_stairs(env,evidence):
    r=ItemSteps(env)
    r.check(3)
    m=env.pyboy.memory
    if list(m[0xDB00:0xDB02]) != [4,1] or m[0xDBD0]!=1:
        raise RouteBlocker('Beetles require shield B, sword A and one key')
    r.move(3,'left',lambda s:s['x']<=136)
    r.move(3,'down',lambda s:s['y']>=64)
    last_swing=-32
    for _ in range(900):
        s=r.check(3,(8,0xEC,0x110))
        if s['dialog_state']:
            dismiss_dialogue(env,precise=True)
            continue
        beetles=[i for i in range(16) if m[0xC280+i] and m[0xC3A0+i]==44]
        targets=[i for i in beetles if m[0xC280+i]==5]
        if not beetles:
            env.step_buttons([],action_frames=1)
            r.check(3)
            break
        if not targets:
            env.step_buttons([],action_frames=1)
            continue
        i=min(targets,key=lambda i:abs(int(m[0xC200+i])-s['x'])+abs(int(m[0xC210+i])-s['y']))
        dx=int(m[0xC200+i])-s['x'];dy=int(m[0xC210+i])-s['y']
        flipped=m[0xC290+i]==3
        if flipped:dy-=int(m[0xC310+i])
        direction=('right' if dx>=0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>=0 else 'up')
        facing=dict(right=0,left=1,up=2,down=3)[direction]
        buttons=['b']
        # Safe approach lanes form a cross: the central column reaches the
        # top floor, while the middle row connects both outside aisles.
        # This permits charge alignment and finishing flipped targets without
        # following them diagonally towards a corner pit.
        ex,ey=int(m[0xC200+i]),int(m[0xC210+i])
        if 48<=ex<=120 and ey<56:
            gx,gy=max(64,min(104,ex)),max(24,ey)
        else:
            gx,gy=max(24,min(136,ex)),max(64,min(80,ey))
        if (gx<64 or gx>104) and not 64<=s['y']<=80:
            gx,gy=max(64,min(104,s['x'])),72
        elif gy<64 and not 64<=s['x']<=104:
            gx,gy=max(64,min(104,s['x'])),72
        tx,ty=gx-s['x'],gy-s['y']
        aligned=abs(dy)<=8 if direction in ('left','right') else abs(dx)<=8
        in_reach=abs(dx)<=24 and abs(dy)<=24
        walk=None
        if flipped and aligned and in_reach:
            if m[0xFF9E]!=facing:walk=direction
            elif not m[0xC137] and env.frames-last_swing>=24:
                buttons.append('a');last_swing=env.frames
        elif flipped and in_reach and not aligned:
            candidate=('down' if dy>0 else 'up') if direction in ('left','right') else ('right' if dx>0 else 'left')
            nx=s['x']+{'left':-1,'right':1}.get(candidate,0)
            ny=s['y']+{'up':-1,'down':1}.get(candidate,0)
            if (64<=nx<=104 and 24<=ny<=88) or (24<=nx<=136 and 64<=ny<=80):walk=candidate
            elif m[0xFF9E]!=facing:walk=direction
        elif abs(dx)+abs(dy)>24 and (abs(tx)>2 or abs(ty)>2):
            walk=('right' if tx>0 else 'left') if abs(tx)>abs(ty) else ('down' if ty>0 else 'up')
        elif m[0xFF9E]!=facing:walk=direction
        if walk:buttons.append(walk)
        env.step_buttons(buttons,action_frames=1)
    else:raise RouteBlocker('Spiked beetle budget exhausted')
    r.move(3,'up' if snapshot(env.pyboy)['y']>80 else 'down',lambda s:78<=s['y']<=80)
    r.move(3,'right',lambda s:s['x']>=136)
    r.travel(3,'up',25)
    if m[0xDBD0]!=1:raise RouteBlocker('Beetle stairs inventory mismatch')
    evidence.append(dict(kind='beetles_cleared_stairs',frame=env.frames,state=snapshot(env.pyboy)))


def clear_goombas(env,room,budget=500):
    r=ItemSteps(env);m=env.pyboy.memory;last_swing=-32
    for _ in range(budget):
        s=r.check(room)
        targets=[i for i in range(16) if m[0xC280+i] and m[0xC3A0+i]==159]
        if not targets:
            env.step_buttons([],action_frames=1);r.check(room);return
        i=min(targets,key=lambda i:abs(int(m[0xC200+i])-s['x']))
        dx=int(m[0xC200+i])-s['x'];dy=int(m[0xC210+i])-s['y']
        direction='right' if dx>=0 else 'left';facing=0 if dx>=0 else 1
        buttons=['b']
        if abs(dx)>24 or m[0xFF9E]!=facing:buttons.append(direction)
        elif abs(dy)<=20 and env.frames-last_swing>=24:
            buttons.append('a');last_swing=env.frames
        env.step_buttons(buttons,action_frames=1)
    raise RouteBlocker('Goomba clearance budget exhausted')


def underground_to_ladder_exit(env,evidence,*,recovery=False):
    r=ItemSteps(env);m=env.pyboy.memory
    r.check(25)
    if m[0xDBD0]!=1 or list(m[0xDB00:0xDB02]) != [4,1]:
        raise RouteBlocker('Underground requires one key, shield B and sword A')
    r.move(25,'down',lambda s:s['y']>=110)
    clear_goombas(env,25)
    r.move(25,'left',lambda s:s['x']<=24)
    r.move(25,'up',lambda s:s['y']<=64)
    r.travel(25,'left',24)
    r.move(24,'left',lambda s:s['x']<=136)
    r.move(24,'down',lambda s:s['y']>=88)
    for _ in range(180):
        r.check(24)
        goombas=[i for i in range(16) if m[0xC280+i] and m[0xC3A0+i]==159]
        if len(goombas)!=1:raise RouteBlocker('Expected one ladder Goomba')
        i=goombas[0]
        if m[0xC200+i]<=104 and m[0xC240+i]>=128:break
        env.step_buttons([],action_frames=1)
    else:raise RouteBlocker('Ladder Goomba clearance budget exhausted')
    r.move(24,'down',lambda s:s['y']>=110)
    if recovery:
        from gameboy_agent.half_heart_setup import prepare_half_heart
        prepare_half_heart(env,evidence)
        r=ItemSteps(env)
    clear_goombas(env,24)
    r.move(24,'left',lambda s:s['x']<=40)
    r.travel(24,'up',1)
    if m[0xDBD0]!=1:raise RouteBlocker('Underground exit inventory mismatch')
    evidence.append(dict(kind='underground_exit',frame=env.frames,state=snapshot(env.pyboy)))


def acquire_feather_from_ladder_exit(env,evidence):
    from gameboy_agent.feather_approach import cross_feather_traps
    from gameboy_agent.progression_skills import equip_item
    r=ItemSteps(env);m=env.pyboy.memory
    r.check(1)
    if m[0xDBD0]!=1 or list(m[0xDB00:0xDB04]) != [4,1,12,0]:
        raise RouteBlocker('Feather approach requires unowned Feather, shield B and sword A')
    r.travel(1,'up',28)
    r.travel(28,'up',29)
    cross_feather_traps(env,evidence)
    r.check(29)
    r.move(29,'up',lambda s:s['y']<=58)
    r.chest(29,0xDB03,10,0x97)
    equip_item(env,10,button='b')
    env.step_buttons([],action_frames=1)
    r.check(29)
    if list(m[0xDB00:0xDB02]) != [10,1] or m[0xDB93] or m[0xDB94] or m[0xFFA2] or m[0xC11C]:
        raise RouteBlocker('Feather receipt did not settle with the battle loadout')
    evidence.append(dict(kind='feather_owned_equipped',frame=env.frames,state=snapshot(env.pyboy)))


def reclear_hardhat_return(env,evidence):
    from gameboy_agent.tail_cave_recovery import DisengagingBeetleTeacher
    from gameboy_agent.tail_cave_teacher import entities
    r=ItemSteps(env);teacher=DisengagingBeetleTeacher()
    for _ in range(512):
        s=r.ready(22)
        targets=entities(env,32)
        if not targets:
            evidence.append(dict(kind='hardhat_return_cleared',frame=env.frames,state=s))
            return
        buttons,frames=teacher.action(s,targets)
        for _ in range(frames):
            env.step_buttons(buttons,action_frames=1)
            r.check(22,(8,0xEC))
    raise RouteBlocker('Hardhat return teacher budget exhausted')
