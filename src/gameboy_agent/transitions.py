"""Bounded, frame-by-frame readiness checks for the verified LADX revision.

The gate follows ReadJoypadState in the matched English 1.1 disassembly.
Consecutive stable frames bridge transient identities during room loading.
"""
from dataclasses import dataclass, field

BUTTONS = ('up', 'down', 'left', 'right', 'a', 'b', 'start', 'select')


def read_phase(boy):
    memory = boy.memory
    return {'gameplay': memory[0xDB95], 'subtype': memory[0xDB96],
            'scroll': memory[0xC124], 'sequence': memory[0xC16B],
            'palette': memory[0xDDD5],
            'room': (memory[0xDBA5], memory[0xFFF7], memory[0xFFF6]),
            'health': memory[0xDB5A]}


def world_ready(phase):
    return (phase['gameplay'] == 0x0B and phase['subtype'] == 7
            and phase['scroll'] == 0 and phase['sequence'] == 4
            and phase['palette'] == 0)


def map_ready(phase):
    # WorldMapInteractiveHandler accepts joypad input at gameplay 7/subtype 5.
    return phase["gameplay"] == 7 and phase["subtype"] == 5


@dataclass
class TransitionTracker:
    stable_required: int = 8
    stable_count: int = 0
    last_room: tuple | None = None
    committed_room: tuple | None = None
    waiting: bool = True
    transitions: int = 0

    def observe(self, phase):
        if world_ready(phase):
            self.stable_count = self.stable_count + 1 if phase['room'] == self.last_room else 1
            if self.stable_count >= self.stable_required:
                if self.committed_room is not None and self.committed_room != phase['room']:
                    self.transitions += 1
                self.committed_room = phase['room']
                self.waiting = False
        else:
            self.stable_count = 0
            self.waiting = True
        self.last_room = phase['room']
        return not self.waiting and world_ready(phase)


class TransitionTimeout(RuntimeError):
    pass


def advance(boy, tracker, pressed, *, action_frames=10, max_wait=600):
    """Deliver the entire action budget on ready frames, release during waits.

    Returns only after a stable phase, or on health-zero death. A timeout is an
    explicit error, never a fake terminal/completion result.
    """
    used = waited = frames = 0
    held = None
    phase = read_phase(boy)
    while True:
        ready = tracker.observe(phase) or map_ready(phase)
        if phase['health'] == 0 or (used >= action_frames and ready):
            break
        if not ready and waited >= max_wait:
            raise TransitionTimeout(f'Transition did not settle after {waited} frames: {phase}')
        wanted = frozenset(pressed) if ready and used < action_frames else frozenset()
        if held != wanted:
            for button in BUTTONS:
                (boy.button_press if button in wanted else boy.button_release)(button)
            held = wanted
        boy.tick(1, render=True)
        frames += 1
        if ready:
            used += 1
        else:
            waited += 1
        phase = read_phase(boy)
    return {'frames_advanced': frames, 'action_frames': used, 'wait_frames': waited,
            'stable_room': tracker.committed_room, 'phase': phase}
