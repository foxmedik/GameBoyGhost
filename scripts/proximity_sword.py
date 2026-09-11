"""Experimental teacher-only sword gate; verified LADX 1.1 read-only inputs."""
# Conservative known enemy/hazard/projectile types; excludes NPCs and pickups.
THREATS=frozenset([0x09,0x0A,0x0B,0x0C,0x0D,0x0E,0x0F,0x10,0x11,0x12,0x14,
 0x15,0x16,0x17,0x18,0x19,0x1A,0x1B,0x1C,0x1E,0x1F,0x20,0x21,0x22,0x23,
 0x24,0x27,0x28,0x29,0x2A,0x2B,0x2C,0x7A,0x99,0xAE,0xB2,0xB9,0xC5,0xC6,0xE4,0xF8,0xF9])

def gate(action,*,dialogue,sword_button,sword_state,entities,x,y,radius=32):
    """Suppress only an already-proposed sword press; never alter movement."""
    action=list(action)
    if dialogue or not sword_button or action[1]!=sword_button:return action,'unchanged'
    if sword_state in (1,2,3,4):return [action[0],0],'swing_active'
    near=any(e['status'] and e['type'] in THREATS and (e['x']-x)**2+(e['y']-y)**2<=radius**2 for e in entities)
    return (action,'near_threat') if near else ([action[0],0],'no_near_threat')

def inputs(base):
    m=base.pyboy.memory
    return dict(sword_state=int(m[0xC137]),x=int(m[0xFF98]),y=int(m[0xFF99]),
      entities=[dict(slot=i,status=int(m[0xC280+i]),type=int(m[0xC3A0+i]),x=int(m[0xC200+i]),y=int(m[0xC210+i])) for i in range(16) if m[0xC280+i]])
