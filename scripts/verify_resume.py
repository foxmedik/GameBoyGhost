"""Recompute a saved training suffix and compare exact policy/optimizer state."""
import argparse
import json
from pathlib import Path
import sys
import time

import torch
from stable_baselines3 import PPO

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.checkpoint import restore_checkpoint, fingerprint


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('checkpoint',type=Path)
    parser.add_argument('expected',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    # Load reference first; restore below then reinstates RNG state.
    reference=PPO.load(args.expected/'policy.zip',device='cpu')
    expected=json.loads((args.expected/'manifest.json').read_text())
    model,env,state=restore_checkpoint(args.checkpoint,next(ROOT.glob('*.gbc')))
    started=time.monotonic()
    try:
        stop=expected['num_timesteps']
        _,callback=model._setup_learn(state['target_timesteps']-model.num_timesteps,None,False,'verify',False)
        callback.on_training_start({}, {})
        while model.num_timesteps<stop:
            model.collect_rollouts(model.env,callback,model.rollout_buffer,n_rollout_steps=model.n_steps)
            model._update_current_progress_remaining(model.num_timesteps,state['target_timesteps'])
            model.train()
        assert model.num_timesteps==stop
        assert fingerprint(env)==expected['fingerprint'], 'Environment fingerprint differs'
        for name,value in reference.policy.state_dict().items():
            assert torch.equal(value,model.policy.state_dict()[name]), f'Policy differs: {name}'
        ref_optimizer=reference.policy.optimizer.state_dict()
        actual=model.policy.optimizer.state_dict()
        assert ref_optimizer['param_groups']==actual['param_groups']
        for key,fields in ref_optimizer['state'].items():
            for name,value in fields.items():
                other=actual['state'][key][name]
                assert torch.equal(value,other) if torch.is_tensor(value) else value==other
        report={'status':'passed','checkpoint':str(args.checkpoint.resolve()),
                'expected':str(args.expected.resolve()),'final_timesteps':stop,
                'environment_exact':True,'policy_exact':True,'optimizer_exact':True,
                'seconds':time.monotonic()-started}
        with args.output.open('x') as f:json.dump(report,f,indent=2)
        print(json.dumps(report))
    finally:env.close()


if __name__=='__main__':main()
