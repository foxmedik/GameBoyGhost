"""Versioned guided progression surface. Physical buttons; no inventory assistance.

Legacy TrainingEnv remains unchanged. Structured observations are privileged,
read-only with respect to game RAM, and retain their historical feature layout.
"""
from copy import deepcopy

import gymnasium as gym
from pyboy import PyBoy

from gameboy_agent.training_env import TrainingEnv
from gameboy_agent.transitions import BUTTONS, TransitionTimeout, world_ready
from gameboy_agent.progression import ProgressJournal, snapshot, mode
from gym_env.const.inventory import Inventory
from gym_env.memory import RamAddress


def advance_progression(boy, tracker, pressed, *, action_frames=10, max_wait=600,
                        max_frames=None, observe=None):
    """Ready-frame budget including inventory/status screens; bounded waiting.

    Start/select commands should be one-frame pulses followed by a release.
    Held movement/A/B retains the legacy timing for existing controllers.
    """
    used = waited = frames = 0
    held = None
    while True:
        state = snapshot(boy)
        ready = tracker.observe(state['phase'])
        ready = ready or mode(state) in ('inventory', 'inventory_status', 'world_map')
        if observe:
            observe(state, frames, not tracker.waiting and world_ready(state['phase']))
        if (state['health'] == 0 or (used >= action_frames and ready)
                or (max_frames is not None and frames >= max_frames)):
            break
        if not ready and waited >= max_wait:
            raise TransitionTimeout(f'Progression transition did not settle: {state["phase"]}')
        wanted = frozenset(pressed) if ready and used < action_frames else frozenset()
        if wanted != held:
            for button in BUTTONS:
                (boy.button_press if button in wanted else boy.button_release)(button)
            held = wanted
        boy.tick(1, render=True)
        frames += 1
        if ready:
            used += 1
        else:
            waited += 1
    return dict(frames_advanced=frames, action_frames=used, wait_frames=waited,
                stable_room=tracker.committed_room, phase=state['phase'], mode=mode(state))


class ProgressionEnv(TrainingEnv):
    def __init__(self, *args, max_frames=300000, reject_completed_start=True,
                 completion_milestone='tail_cave_entered', **kwargs):
        if max_frames < 1:
            raise ValueError('Frame budget must be positive')
        self.max_frames = max_frames
        self.reject_completed_start = reject_completed_start
        self.completion_milestone = completion_milestone
        super().__init__(*args, sword_curriculum=False, **kwargs)
        self.action_space = gym.spaces.MultiDiscrete((5, 3))
        self.journal = None
        self.frames = 0

    def script_give_magic_powder(self):
        # Disabled even if a future inherited method calls this entry point.
        return None

    def switch_inventory(self):
        raise RuntimeError('Progression requires physical inventory controls')

    def upon_reset(self):
        # No inherited reward/checkpoint bookkeeping against a fresh emulator.
        pass

    def post_state_load(self):
        self.reset_obs()
        for button in BUTTONS:
            self.pyboy.button_release(button)
        self.start_episode_reward_dict = {}
        self.last_step_reward_dict = {}

    def run_action_on_emulator(self, action):
        raise RuntimeError('Use progression step/step_buttons for recorded physical controls')

    def get_inventory_progress(self):
        # Preserve feature ordering without invoking the inherited refill getter.
        m = self.pyboy.memory
        slots = m[0xDB00:0xDB0C]
        result = {}
        for name, address, value, weight in (
            ('FLIPPERS', RamAddress.wHasFlippers.value, 0xFF, 1),
            ('MEDICINE', RamAddress.wHasMedicine.value, 0xFF, 1),
            ('TOADSTOOL', 0xDB4B, 1, -0.5),
            ('TAIL_KEY', 0xDB11, None, 1),
            ('FACE_KEY', RamAddress.wHasFaceKey.value, 0xFF, 1),
            ('ANGLER_KEY', RamAddress.wHasAnglerKey.value, 0xFF, 1),
            ('BIRD_KEY', RamAddress.wHasBirdKey.value, 0xFF, 1),
        ):
            result[name] = int(bool(m[address]) if value is None else m[address] == value) * weight
        result.update({item.name: int(item.value in slots) for item in Inventory if item != Inventory.EMPTY})
        return result

    def reset(self, *, seed=None, options=None):
        # Fresh host/renderer state prevents history leaking across resets.
        self.close()
        self.pyboy = PyBoy(str(self.config['gb_path']), window='null')
        self.pyboy.set_emulation_speed(0)
        self.frames = 0
        self.journal = None
        try:
            obs, info = super().reset(seed=seed, options=options)
            self.frames = self.last_timing['frames_advanced']
            initial = snapshot(self.pyboy)
            self.journal = ProgressJournal(initial, reject_completed_start=self.reject_completed_start)
            self.journal.observe(initial, frame=self.frames, decision=0, settled=True)
            return obs, {**info, 'progression': initial, 'assistance': 'structured_read_only_game_state'}
        except BaseException:
            self.needs_reset = True
            raise

    def step_input_events(self, press=(), *, release=(), frames=1, release_after=()):
        """Clocked physical input events for timed interactions and teacher traces.

        Unlike ready-frame commands, these advance exactly the requested emulator
        frames, including animations. Unmentioned buttons retain their state.
        Every frame still passes through the journal, death and episode budget.
        Releases after the interval are queued for the next emulator frame, as
        with PyBoy's physical button interface. No game RAM is assigned.
        """
        if self.needs_reset:
            raise RuntimeError('Reset is required before stepping')
        press, release, release_after = tuple(press), tuple(release), tuple(release_after)
        for group in (press, release, release_after):
            if len(set(group)) != len(group) or any(b not in BUTTONS for b in group):
                raise ValueError('Invalid physical input events')
        if (set(press) & set(release) or {'up', 'down'} <= set(press)
                or {'left', 'right'} <= set(press)
                or type(frames) is not int or not 1 <= frames <= 600):
            raise ValueError('Invalid physical input events or frame duration')
        event_start = len(self.journal.events)
        advanced = 0
        try:
            for button in release:
                self.pyboy.button_release(button)
            for button in press:
                self.pyboy.button_press(button)
            for _ in range(min(frames, max(0, self.max_frames-self.frames))):
                if snapshot(self.pyboy)['health'] == 0:
                    break
                self.pyboy.tick(1, render=True)
                self.frames += 1
                advanced += 1
                current = snapshot(self.pyboy)
                settled = self.transition_tracker.observe(current['phase'])
                self.journal.observe(current, frame=self.frames,
                                     decision=self.total_steps, settled=settled)
            for button in release_after:
                self.pyboy.button_release(button)
            current = snapshot(self.pyboy)
            self.last_timing = dict(frames_advanced=advanced, action_frames=advanced,
                                    wait_frames=0, phase=current['phase'], mode=mode(current),
                                    stable_room=self.transition_tracker.committed_room,
                                    timing='emulated_frames')
            return self._finish_command(dict(buttons=list(press), release=list(release),
                release_after=list(release_after), action_frames=frames,
                legacy_action=[0, 0], timing='emulated_frames'), event_start)
        except BaseException:
            self.needs_reset = True
            raise

    def step(self, action):
        if not self.action_space.contains(action):
            raise ValueError(f'Invalid progression action (inventory RAM action forbidden): {action}')
        movement, button = (int(v) for v in action)
        pressed = [v for v in ((None, 'up', 'down', 'left', 'right')[movement],
                               (None, 'a', 'b')[button]) if v]
        return self.step_buttons(pressed, legacy_action=[movement, button])

    def step_buttons(self, pressed, *, action_frames=10, legacy_action=None):
        if self.needs_reset:
            raise RuntimeError('Reset is required before stepping')
        pressed = tuple(pressed)
        if (len(set(pressed)) != len(pressed) or any(v not in BUTTONS for v in pressed)
                or not isinstance(action_frames, int) or not 1 <= action_frames <= 60
                or {'up', 'down'} <= set(pressed) or {'left', 'right'} <= set(pressed)):
            raise ValueError('Invalid physical button command or duration')
        if ('start' in pressed or 'select' in pressed) and (len(pressed) != 1 or action_frames != 1):
            raise ValueError('Menu buttons require a single-button, one-frame pulse')
        event_start = len(self.journal.events)
        base_frame = self.frames
        def observed(state, local_frame, settled):
            self.frames = base_frame + local_frame
            self.journal.observe(state, frame=self.frames, decision=self.total_steps, settled=settled)
        try:
            self.last_timing = advance_progression(self.pyboy, self.transition_tracker, pressed,
                                                  action_frames=action_frames,
                                                  max_frames=max(0, self.max_frames-base_frame),
                                                  observe=observed)
        except BaseException:
            self.needs_reset = True
            raise
        return self._finish_command(dict(buttons=list(pressed), action_frames=action_frames,
                                         legacy_action=list(legacy_action or [0, 0])), event_start)

    def _finish_command(self, command, event_start):
        # Keep legacy feature encoding bounded for controllers; exact physical
        # commands and durations are retained separately in episode_actions.
        self.last_action = tuple(command['legacy_action'])
        self.total_steps += 1
        self.episode_actions.append(command)
        # Maintain observation novelty without calling inherited shaped rewards.
        self.seen_pos.add(self.get_world_pos())
        self.seen_map.add(self.get_map_pos())
        obs = self.get_observation()
        self.cached_observation = deepcopy(obs)
        current = snapshot(self.pyboy)
        dead = current['health'] == 0
        success = bool(not dead and self.completion_milestone
                       and self.completion_milestone in self.journal.milestones)
        terminated = dead or success
        truncated = self.total_steps >= self.config['max_steps'] or self.frames >= self.max_frames
        self.done = self.needs_reset = bool(terminated or truncated)
        self.last_map_pos = self.get_map_pos()
        return obs, 0.0, bool(terminated), bool(truncated), dict(
            **deepcopy(self.last_timing), progression=current,
            events=deepcopy(self.journal.events[event_start:]),
            milestones=deepcopy(self.journal.milestones),
            damage_raw=self.journal.damage_raw, healing_raw=self.journal.healing_raw,
            death=dead, task_success=success, reward={},
            completion=('tail_key_and_entry' if success and self.completion_milestone == 'tail_cave_entered'
                        else self.completion_milestone if success else None),
            completion_evaluated=True, detector_validation='source_grounded_pending_live_quest_fixtures',
            assistance='structured_read_only_game_state')
