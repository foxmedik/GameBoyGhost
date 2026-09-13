"""Bounded encounter ownership using the qualified deterministic room teacher."""
from gameboy_agent.progression import snapshot
from gameboy_agent.tail_cave_progression import GEL, clear_compass_room
from gameboy_agent.tail_cave_teacher import entities


class TakeoverBlocked(RuntimeError):
    pass


class BoundedInputs:
    """Budget every physical command, including commands inside dialogue helpers."""
    def __init__(self, env, max_commands=512, max_frames=8192):
        self.env = env
        self.max_commands = max_commands
        self.max_frames = max_frames
        self.start_frame = env.frames
        self.commands = 0

    def __getattr__(self, name):
        return getattr(self.env, name)

    def _step(self, method, expected_frames, *args, **kwargs):
        if self.commands >= self.max_commands:
            raise TakeoverBlocked('physical command budget exhausted')
        if self.env.frames - self.start_frame + expected_frames > self.max_frames:
            raise TakeoverBlocked('emulated frame budget exhausted')
        self.commands += 1
        result = method(*args, **kwargs)
        if self.env.frames - self.start_frame > self.max_frames:
            raise TakeoverBlocked('physical command exceeded frame budget')
        return result

    def step_buttons(self, buttons, *, action_frames=1, **kwargs):
        return self._step(self.env.step_buttons, action_frames, buttons,
                          action_frames=action_frames, **kwargs)

    def step_input_events(self, buttons=(), *, frames=1, **kwargs):
        return self._step(self.env.step_input_events, frames, buttons,
                          frames=frames, **kwargs)


class EncounterTakeover:
    def __init__(self):
        self.used = False

    def run(self, env, evidence, *, max_commands=512):
        state = snapshot(env.pyboy)
        if self.used:
            raise TakeoverBlocked('encounter takeover already used')
        if state['room'] != [1, 0, 21] or state['health'] <= 0:
            raise TakeoverBlocked(f'living room15 required: {state}')
        if not entities(env, GEL):
            raise TakeoverBlocked('takeover requires an active encounter')
        self.used = True
        bounded = BoundedInputs(env, max_commands=min(512, max_commands))
        clear_compass_room(bounded, evidence, budget=512)
        state = snapshot(env.pyboy)
        if state['room'] != [1, 0, 21] or state['health'] <= 0 or entities(env, GEL):
            raise TakeoverBlocked('living room-clear contract failed')
        return bounded.commands
