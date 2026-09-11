"""Structured baseline with phase-aware controls and resumable episode history."""
from copy import deepcopy

from gameboy_agent.ladx_baseline import BaselineEnv
from gameboy_agent.transitions import TransitionTracker, advance


class TrainingEnv(BaselineEnv):
    def __init__(self, *args, sword_curriculum=False, **kwargs):
        self.sword_curriculum = sword_curriculum
        super().__init__(*args, **kwargs)
        self.episode_actions = []
        self.episode_seed = None
        self.transition_tracker = TransitionTracker()
        self.last_timing = {}

    def reset(self, *, seed=None, options=None):
        self.episode_actions = []
        self.episode_seed = seed
        self.transition_tracker = TransitionTracker()
        obs, info = super().reset(seed=seed, options=options)
        # Initial savestate is a verified gameplay state. Settle through the
        # same readiness gate used between policy actions before observing.
        self.last_timing = advance(self.pyboy, self.transition_tracker, (), action_frames=0)
        obs = self.get_observation()
        self.last_map_pos = self.get_map_pos()
        self.cached_observation = deepcopy(obs)
        self.initial_sword_level = int(self.pyboy.memory[0xDB4E])
        if self.sword_curriculum and self.initial_sword_level != 0:
            raise ValueError("Sword curriculum must start without a sword")
        return obs, info

    def run_action_on_emulator(self, action):
        movement = (None, 'up', 'down', 'left', 'right')[int(action[0])]
        button = (None, 'a', 'b', None)[int(action[1])]
        if int(action[1]) == 3 and self.last_action[1] != 3:
            self.switch_inventory()  # Explicit reproduction privilege, not neutral.
        self.register_push_sfx()
        self.register_block_sfx()
        self.register_collision()
        self.register_sword_dmg()
        try:
            self.last_timing = advance(self.pyboy, self.transition_tracker,
                                       [x for x in (movement, button) if x])
        finally:
            self.deregister_push_sfx()
            self.deregister_block_sfx()
            self.deregister_collision()
            self.deregister_sword_dmg()
        self.push_reward = self.push_sfx
        self.push_sfx = False
        self.script_give_magic_powder()
        self.last_action = tuple(int(x) for x in action)
        self.total_steps += 1

    def get_push_reward(self):
        # Consume the event exactly once without re-registering an emulator
        # hook from a reward getter. Reward remains explicitly assisted.
        if self.push_reward:
            self.count_push_sfx += 1
            self.push_reward = False
        return self.count_push_sfx

    def step(self, action):
        result = super().step(action)
        self.episode_actions.append([int(x) for x in action])
        self.cached_observation = deepcopy(result[0])
        result[4].update(deepcopy(self.last_timing))
        obs, reward, terminated, truncated, info = result
        sword_acquired = self.initial_sword_level == 0 and self.pyboy.memory[0xDB4E] > 0
        info.update(sword_acquired=bool(sword_acquired), death=bool(self.pyboy.memory[0xDB5A] == 0))
        if self.sword_curriculum:
            # Objective-specific sparse curriculum reward, separately labeled.
            reward = 10.0 if sword_acquired else (-1.0 if info['death'] else -0.001)
            info['baseline_reward_components'] = info['reward']
            info['reward'] = {'sword_curriculum': reward}
            info['task_success'] = bool(sword_acquired)
            terminated = terminated or sword_acquired
            self.done = self.needs_reset = bool(terminated or truncated)
        return obs, reward, bool(terminated), truncated, info
