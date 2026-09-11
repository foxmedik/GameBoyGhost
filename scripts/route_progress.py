"""Ordered, budgeted waypoint progress; no navigation decisions."""
from gameboy_agent.navigation import reached


def advance(state,goals,progress,total_steps,budget):
    if state.health==0:return 'death'
    while progress['cursor']<len(goals):
        goal=goals[progress['cursor']]
        if not reached(state.room,state.x,state.y,goal):break
        progress['completed'].append(dict(index=progress['cursor'],step=total_steps,actions=progress['leg_steps'],
            room=list(state.room),x=state.x,y=state.y,health=state.health))
        progress['cursor']+=1;progress['leg_steps']=0;progress['leg_start']=total_steps
    if progress['cursor']==len(goals):return 'success'
    if progress['leg_steps']>=budget:return 'navigation_timeout'
    return 'running'
