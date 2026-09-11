"""Learned, goal-conditioned local navigation; only physical movement/A/B."""
import numpy as np
import torch
from torch import nn


def encode(obs, room, target_room, target_x, target_y):
    room=np.asarray(room);goal=np.asarray(target_room)
    bits=lambda value: ((value[:,None].astype(np.int64) >> np.arange(8)) & 1).reshape(-1)
    x,y=obs['control'][:2]*255
    goal_features=np.array([target_x/160,target_y/144,(target_x-x)/160,(target_y-y)/144,
                           (goal[2]%16-room[2]%16)/16,(goal[2]//16-room[2]//16)/16,
                           float(np.array_equal(room,goal))],dtype=np.float32)
    return np.concatenate([obs['control'],obs['vector'][:10],obs['entity_type']/255,
        np.clip(obs['entity_info'].reshape(-1),-2,2),obs['minimap_object'][3:8,3:8].reshape(-1)/255,
        obs['minimap_info'][3:8,3:8,:3].reshape(-1),bits(room),bits(goal),goal_features]).astype(np.float32)


def reached(room,x,y,goal,tolerance=8):
    return list(room)==list(goal['room']) and abs(x-goal['x'])+abs(y-goal['y'])<=tolerance


class NavigationNet(nn.Module):
    def __init__(self,inputs):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(inputs,256),nn.ReLU(),nn.Linear(256,256),nn.ReLU(),nn.Linear(256,8))
    def forward(self,x):return self.net(x)


class NavigationController:
    def __init__(self,checkpoint):
        saved=torch.load(checkpoint,map_location='cpu')
        self.model=NavigationNet(saved['inputs']);self.model.load_state_dict(saved['model']);self.model.eval()
        self.mean=saved['mean'];self.scale=saved['scale']
        self.mask=saved.get('input_mask',np.ones(saved['inputs'],dtype=np.float32))
        self.goal_experts={}
        for expert in saved.get('goal_experts',[]):
            goal=expert['goal'];key=tuple(goal['room'])+(goal['x'],goal['y'])
            if len(goal['room'])!=3 or key in self.goal_experts:
                raise ValueError('Invalid or duplicate navigation expert goal')
            model=NavigationNet(saved['inputs']);model.load_state_dict(expert['model']);model.eval()
            self.goal_experts[key]=model
    def action(self,obs,room,goal):
        x=encode(obs,room,goal['room'],goal['x'],goal['y'])
        model=self.goal_experts.get(tuple(goal['room'])+(goal['x'],goal['y']),self.model)
        with torch.no_grad():logits=model(torch.from_numpy((x-self.mean)/self.scale*self.mask))
        return [int(logits[:5].argmax()),int(logits[5:].argmax())]
