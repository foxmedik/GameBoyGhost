"""Read-only evidence and milestone candidates for the matched English 1.1 ROM.

Raw transitions are observations, never inferred causes. Physical quest fixtures
must validate source-grounded milestone candidates before a completion claim.
"""
from collections import Counter
from copy import deepcopy

from gameboy_agent.transitions import read_phase, world_ready


def snapshot(boy):
    m = boy.memory
    phase = read_phase(boy)
    return dict(phase=phase, room=list(phase['room']), x=int(m[0xFF98]), y=int(m[0xFF99]),
                health=int(m[0xDB5A]), max_hearts=int(m[0xDB5B]),
                inventory=list(m[0xDB00:0xDB0C]), sword=int(m[0xDB4E]),
                toadstool=int(m[0xDB4B]), powder=int(m[0xDB4C]),
                bombs=int(m[0xDB4D]), arrows=int(m[0xDB45]),
                tail_key=int(m[0xDB11]), tarin=int(m[0xDB48]),
                tail_door_status=int(m[0xD8D3]), trade_item=int(m[0xDB0E]),
                dialog_state=int(m[0xC19F]), dialog_id=int(m[0xC173]) + 256 * int(m[0xC112]),
                inventory_cursor=int(m[0xDBA3]))


def mode(state):
    phase = state['phase']
    if state['health'] == 0:
        return 'dead'
    if phase['gameplay'] == 0x0C and phase['subtype'] == 8:
        return 'inventory'
    if phase['gameplay'] == 0x0C and phase['subtype'] == 0x0A:
        return 'inventory_status'
    if phase['gameplay'] == 7 and phase['subtype'] == 5:
        return 'world_map'
    if world_ready(phase):
        return 'dialogue' if state['dialog_state'] else 'world'
    return 'transition'


def at_tail_entrance(state):
    return state['room'] == [1, 0, 0x17]


class ProgressJournal:
    def __init__(self, initial, *, reject_completed_start=True):
        if reject_completed_start and (initial['tail_key'] or initial['tail_door_status'] & 0x10
                                       or at_tail_entrance(initial)):
            raise ValueError('Fresh quest requires no initial Tail Key, open entrance or Tail Cave entry')
        self.previous = deepcopy(initial)
        self.events = []
        self.milestones = {}
        self.damage_raw = 0
        self.healing_raw = 0
        self.committed_room = None
        self.initial_disqualified = bool(initial['tail_key'] or initial['tail_door_status'] & 0x10
                                         or at_tail_entrance(initial))

    def state(self):
        return deepcopy(vars(self))

    @classmethod
    def restore(cls, value):
        journal = cls(value['previous'], reject_completed_start=False)
        vars(journal).update(deepcopy(value))
        return journal

    def observe(self, current, *, frame, decision, settled=False):
        previous = self.previous
        start = len(self.events)

        def emit(kind, text, **details):
            event = dict(id=len(self.events), frame=frame, decision=decision, kind=kind,
                         room=current['room'], position=[current['x'], current['y']],
                         text=text, evidence='observed_ram_transition', details=details)
            self.events.append(event)
            return event

        def milestone(name, text, **details):
            if name not in self.milestones:
                self.milestones[name] = emit(name, text, **details)['id']

        delta = current['health'] - previous['health']
        if delta < 0:
            self.damage_raw -= delta
            emit('health_lost', f'Health decreased by {-delta} raw units; cause unassigned.',
                 before=previous['health'], after=current['health'], cause=None)
        elif delta > 0:
            self.healing_raw += delta
            emit('health_gained', f'Health increased by {delta} raw units.',
                 before=previous['health'], after=current['health'])
        if previous['health'] and current['health'] == 0:
            emit('death', 'Health reached zero.')
        if current['inventory'] != previous['inventory']:
            before, after = Counter(previous['inventory']), Counter(current['inventory'])
            added = list((after - before).elements())
            removed = list((before - after).elements())
            emit('inventory_changed', 'Inventory slots changed.', before=previous['inventory'],
                 after=current['inventory'], added=[v for v in added if v],
                 removed=[v for v in removed if v])
        for field in ('powder', 'bombs', 'arrows', 'trade_item', 'toadstool'):
            if previous[field] != current[field]:
                emit(field + '_changed', f'{field} changed from {previous[field]} to {current[field]}.',
                     before=previous[field], after=current[field])
        if current['dialog_state'] and (not previous['dialog_state'] or
                                       current['dialog_id'] != previous['dialog_id']):
            emit('dialogue_observed', f'Dialogue {current["dialog_id"]:03X} opened; text not decoded.',
                 dialog_id=current['dialog_id'], exact_text=None, speaker=None)
        if previous['dialog_state'] and not current['dialog_state']:
            emit('dialogue_closed', 'Dialogue closed.')
        if not previous['sword'] and current['sword']:
            milestone('sword_acquired', 'Sword possession appeared.', raw=current['sword'])
        if not previous['toadstool'] and current['toadstool'] == 1:
            milestone('toadstool_acquired', 'Toadstool possession appeared.')
        powder_available = lambda s: not s['toadstool'] and s['powder'] > 0 and 0x0C in s['inventory']
        if powder_available(current) and not powder_available(previous):
            milestone('powder_available', 'Powder is present with a positive count and no toadstool.',
                      count=current['powder'])
        if previous['tarin'] == 0 and current['tarin'] == 1:
            milestone('raccoon_cured', 'Tarin flag changed from 0 to 1.', before=0, after=1)
        if not previous['tail_key'] and current['tail_key']:
            milestone('tail_key_acquired', 'Tail Key possession appeared.', raw=current['tail_key'])
        if not previous['tail_door_status'] & 0x10 and current['tail_door_status'] & 0x10:
            milestone('tail_cave_opened', 'Tail Cave exterior event bit became set.')
        if settled and world_ready(current['phase']):
            if self.committed_room is not None and self.committed_room != current['room']:
                emit('room_transition', f'Reached room {current["room"]}.',
                     from_room=self.committed_room, to_room=current['room'], reverse_verified=False)
            self.committed_room = current['room'][:]
            if (not self.initial_disqualified and current['health'] > 0
                    and not current['dialog_state'] and at_tail_entrance(current)
                    and 'tail_key_acquired' in self.milestones
                    and 'tail_cave_opened' in self.milestones):
                milestone('tail_cave_entered', 'Reached the settled Tail Cave entrance alive after acquiring the key and opening the entrance.')
        self.previous = deepcopy(current)
        return self.events[start:]
