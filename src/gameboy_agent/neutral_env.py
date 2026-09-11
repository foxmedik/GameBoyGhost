"""Unassisted emulator surface: framebuffer and physical buttons only.

No completion detector is implemented yet. This is an evaluation foundation,
not a finished game-completion benchmark or a reward-bearing training task.
"""
import io
from pathlib import Path

import gymnasium as gym
import numpy as np
from pyboy import PyBoy


class NeutralEnv(gym.Env):
    metadata = {'render_modes': ['rgb_array']}
    buttons = ('up', 'down', 'left', 'right', 'a', 'b', 'start', 'select')

    def __init__(self, rom: Path, state: Path | None = None, *, frames_per_step=10,
                 max_steps=128):
        if frames_per_step < 1 or max_steps < 1:
            raise ValueError('Frame and step limits must be positive')
        self.render_mode = 'rgb_array'
        self.frames_per_step = frames_per_step
        self.max_steps = max_steps
        self.rom = Path(rom)
        self.action_space = gym.spaces.MultiBinary(len(self.buttons))
        self.observation_space = gym.spaces.Box(0, 255, (144, 160, 3), np.uint8)
        self.pyboy = PyBoy(str(rom), window='null')
        self.pyboy.set_emulation_speed(0)
        if state is not None:
            with Path(state).open('rb') as source:
                self.pyboy.load_state(source)
        initial = io.BytesIO()
        self.pyboy.save_state(initial)
        self.initial = initial.getvalue()
        self.steps = 0
        self.needs_reset = True

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        # PyBoy 2.0 load_state restores the motherboard, but does not reset all
        # host/renderer state. Fresh instances prevent cross-episode leakage.
        self.pyboy.stop(save=False)
        self.pyboy = PyBoy(str(self.rom), window='null')
        self.pyboy.set_emulation_speed(0)
        self.pyboy.load_state(io.BytesIO(self.initial))
        # Release pending controls from the preceding episode/supplied state.
        for button in self.buttons:
            self.pyboy.button_release(button)
        self.steps = 0
        self.needs_reset = False
        return self.render(), {'completion': None, 'completion_evaluated': False}

    def step(self, action):
        if self.needs_reset:
            raise RuntimeError('Reset is required before stepping')
        if not self.action_space.contains(action):
            raise ValueError(f'Invalid physical-button action: {action}')
        for button, pressed in zip(self.buttons, action):
            if pressed:
                self.pyboy.button_press(button)
            else:
                self.pyboy.button_release(button)
        self.pyboy.tick(self.frames_per_step, render=True)
        self.steps += 1
        truncated = self.steps >= self.max_steps
        self.needs_reset = truncated
        return self.render(), 0.0, False, truncated, {
            'frames_advanced': self.frames_per_step,
            'completion': None, 'completion_evaluated': False,
        }

    def render(self):
        return self.pyboy.screen.ndarray[:, :, :3].copy()

    def close(self):
        self.pyboy.stop(save=False)
