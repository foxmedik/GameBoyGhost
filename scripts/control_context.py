"""Explicit privileged controller inputs; no game RAM writes or action override."""
from copy import deepcopy
import gymnasium as gym
import numpy as np
import torch
from gameboy_agent.ladx_baseline import CustomFeatureExtractor

class ControlContext(gym.ObservationWrapper):
    def __init__(self,env):
        super().__init__(env)
        self.observation_space=deepcopy(env.observation_space)
        self.observation_space['control']=gym.spaces.Box(0,1,(5,),np.float32)
    def observation(self,obs):
        m=self.env.pyboy.memory
        return {**obs,'control':np.array([m[0xFF98]/255,m[0xFF99]/255,m[0xC19F]/255,
                                         self.env.last_action[0]/4,self.env.last_action[1]/3],dtype=np.float32)}

class ContextExtractor(CustomFeatureExtractor):
    def __init__(self,observation_space):
        super().__init__(observation_space)
        self._features_dim+=5
    def forward(self,observations):
        return torch.cat((super().forward(observations),observations['control']),dim=-1)

from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
class CompactContextExtractor(BaseFeaturesExtractor):
    """Ablation: use only the five explicit controller inputs."""
    def __init__(self,observation_space):super().__init__(observation_space,features_dim=5)
    def forward(self,observations):
        value=observations['control']
        scale=value.new_tensor([10.,10.,25.,1.,1.])
        offset=value.new_tensor([.33,.32,0.,0.,0.])
        return (value-offset)*scale
