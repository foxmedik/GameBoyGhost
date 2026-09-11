"""Fixed-savestate compatibility baseline; upstream references stay unchanged."""
from copy import deepcopy
from pathlib import Path
import sys

import gymnasium as gym
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / 'references' / 'LADXExperiments'
sys.path.insert(0, str(UPSTREAM / 'experiments'))
from gym_env.link_awake_env import LinkAwakeningEnv, BASE_CONFIG
from model.feature_extraction import CustomFeatureExtractor
from gameboy_agent.rom_profile import RevisionHooks, validate_rom


class BaselineEnv(RevisionHooks, LinkAwakeningEnv):
    """Retains upstream actions/rewards, with fixed starts and strict failures.

    This is a privileged research harness: inventory switching edits RAM and
    observations/rewards include game-specific progression knowledge.
    """

    def __init__(self, rom: Path, state: Path, max_steps=128):
        validate_rom(rom)
        config = deepcopy(BASE_CONFIG)
        config.update(gb_path=str(rom), init_state=str(state), headless=True,
                      max_steps=max_steps, render_all_frames=True)
        super().__init__(config)
        self.pyboy.set_emulation_speed(0)
        self.observation_space['entity_type'] = gym.spaces.Box(0, 255, (16,), np.int32)
        # Offsets are signed; retain values rather than clipping observations.
        self.observation_space['entity_info'] = gym.spaces.Box(-np.inf, np.inf, (16, 4), np.float32)
        # Upstream explicitly encodes possession of the toadstool as -0.5.
        low = np.zeros(89, dtype=np.float32)
        low[12] = -0.5  # 10 base fields + FLIPPERS, MEDICINE, TOADSTOOL
        self.observation_space['vector'] = gym.spaces.Box(low, np.ones(89, dtype=np.float32))
        self.needs_reset = True

    def load_random_checkpoint(self, type='found'):
        return False

    def save_checkpoint_result(self):
        pass

    def reset(self, *, seed=None, options=None):
        gym.Env.reset(self, seed=seed)
        self.checkpoint_loaded = False
        self.checkpoint = None
        obs, info = super().reset(seed=seed)
        self.done = False
        self.last_map_pos = self.get_map_pos()
        self.needs_reset = False
        return obs, info

    def get_observation(self):
        raw = super().get_observation()
        obs = {key: np.asarray(value, dtype=self.observation_space[key].dtype)
               for key, value in raw.items()}
        for key, value in obs.items():
            if not np.isfinite(value).all() or not self.observation_space[key].contains(value):
                raise ValueError(f'Invalid observation {key}: shape={value.shape}, range={value.min(), value.max()}')
        return obs

    def step(self, action):
        if self.needs_reset:
            raise RuntimeError('Reset is required before stepping')
        if not self.action_space.contains(action):
            raise ValueError(f'Invalid action: {action}')
        self.run_action_on_emulator(action)
        obs = self.get_observation()
        previous = self.last_step_reward_dict.copy()
        reward, cumulative = self.get_net_reward()
        components = {key: (self.last_step_reward_dict[key] - value) * self.config['reward_weights'][key]
                      for key, value in previous.items() if key in self.last_step_reward_dict}
        if not np.isfinite(reward):
            raise ValueError('Non-finite reward')
        terminated = bool(self.get_health_reward() == 0)
        truncated = bool(self.total_steps >= self.config['max_steps'])
        self.done = terminated or truncated
        self.needs_reset = self.done
        self.last_map_pos = self.get_map_pos()
        return obs, float(reward), terminated, truncated, {
            'reward': components, 'reward_cumulative': cumulative,
            'completion': None, 'completion_evaluated': False,
        }

    def close(self):
        for deregister in (self.deregister_collision, self.deregister_push_sfx,
                           self.deregister_block_sfx, self.deregister_sword_dmg):
            deregister()
        self.pyboy.stop(save=False)
