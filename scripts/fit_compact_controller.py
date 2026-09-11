"""Small supervised controller ablation on the aggregated corrective data."""
from pathlib import Path
import sys
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import environment,write
from control_context import ControlContext,CompactContextExtractor
from gameboy_agent.checkpoint import digest
out=Path(sys.argv[1]);source=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
torch.set_num_threads(2);data=np.load(source)
env=ControlContext(environment(out/'env','approach'))
model=PPO('MultiInputPolicy',DummyVecEnv([lambda:env]),seed=0,device='cpu',
          policy_kwargs={'features_extractor_class':CompactContextExtractor,'net_arch':[64,64],'activation_fn':torch.nn.ReLU})
obs={k:torch.as_tensor(data[k]) for k in env.observation_space.spaces};actions=torch.as_tensor(data['actions'],dtype=torch.long)
optimizer=torch.optim.Adam(model.policy.parameters(),lr=.001)
generator=torch.Generator().manual_seed(62)
try:
    for epoch in range(300):
        for idx in torch.randperm(len(actions),generator=generator).split(256):
            _,logp,_=model.policy.evaluate_actions({k:v[idx] for k,v in obs.items()},actions[idx])
            loss=-logp.mean();optimizer.zero_grad();loss.backward();optimizer.step()
        if (epoch+1)%50==0:print(epoch+1,float(loss.detach()),flush=True)
    model.save(out/'imitation-policy.zip')
    torch.save({'optimizer':optimizer.state_dict(),'torch_rng':torch.get_rng_state(),'shuffle_rng':generator.get_state(),
                'epochs':300},out/'supervised-state.pt')
    write(out/'provenance.json',{'supervision':'compact_context_behavior_cloning','source':str(source),'source_sha256':digest(source),
          'features':['pixel_x','pixel_y','dialogue_state','previous_movement','previous_button'],
          'scope':'close_start_controller_only','full_game_completion':False})
finally:env.close()
