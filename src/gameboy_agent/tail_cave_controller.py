"""Compact observation for the Tail Cave room-16 specialist."""
import numpy as np
from gameboy_agent.progression import snapshot
from gameboy_agent.tail_cave_teacher import HARDHAT_BEETLE,KEY_DROP_POINT,SMALL_KEYS,entities

def tail_feature(base, history):
    state=snapshot(base.pyboy);px,py=state['x'],state['y'];beetles=sorted(entities(base,HARDHAT_BEETLE),key=lambda e:e['slot']);values=[px/160,py/144,state['health']/24,int(base.pyboy.memory[SMALL_KEYS]),len(beetles)/2]
    for index in range(2):
        if index<len(beetles):
            e=beetles[index];values.extend((1,(e['x']-px)/160,(e['y']-py)/144,e['x']/160,e['y']/144,e['status']/5))
        else:values.extend((0,0,0,0,0,0))
    if beetles:
        target=min(beetles,key=lambda e:abs(e['x']-px)+abs(e['y']-py));push_up=target['y']<=72;stance_y=target['y']+24 if push_up else target['y']-24
        values.extend(((target['x']-px)/160,(target['y']-py)/144,abs(target['x']-px)/160,abs(target['y']-py)/144,float(push_up),(target['x']-px)/160,(stance_y-py)/144))
    else:values.extend((0,0,0,0,0,0,0))
    drops=entities(base,KEY_DROP_POINT)
    if drops:values.extend((1,(drops[0]['x']-px)/160,(drops[0]['y']-py)/144))
    else:values.extend((0,0,0))
    return np.concatenate((np.asarray(values,dtype=np.float32),history)).astype(np.float32)
