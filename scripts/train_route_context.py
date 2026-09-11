"""Preserve close demonstrations while adding full-route corrective examples."""
from pathlib import Path
import sys
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import clone,write
from gameboy_agent.checkpoint import digest
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
parents=[Path('runs/imitation-context-refinement/round-1/demonstrations.npz'),Path('runs/route-teacher-probe-v2/demonstrations.npz')]
data=[np.load(p) for p in parents]
arrays={k:np.concatenate([d[k] for d in data]) for k in data[0].files}
np.savez_compressed(out/'demonstrations.npz',**arrays)
write(out/'demonstrations.json',{'supervision':'feedback_route_and_close_teacher','rows':len(arrays['actions']),
      'parents':[{'path':str(p),'sha256':digest(p)} for p in parents],'action_clock':'ten_ready_frames','harness_privilege':'D'})
torch.set_num_threads(4)
clone(out,80,initial_policy=Path('runs/imitation-context-refinement/round-1/imitation-policy.zip'))
