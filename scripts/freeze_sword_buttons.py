"""Freeze button-only v2 with identical data, optimization and gates to v1."""
import json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.dataset import sha256

def main():
    prior=ROOT/'runs/navigation-sword-v1';out=ROOT/'runs/navigation-sword-v2'
    plan=json.loads((prior/'plan.json').read_text())
    for p,h in plan['baseline_hashes'].items():assert sha256(ROOT/p)==h
    for p in (prior/'data').glob('*/manifest.json'):
        m=json.loads(p.read_text());assert m['replay_verified']
        for a in m['paths']:assert sha256(p.parent/a['file'])==a['sha256']
    out.mkdir(exist_ok=False);shutil.copytree(prior/'data',out/'data');shutil.copy2(prior/'curriculum.json',out/'curriculum.json')
    sources=[Path(__file__),ROOT/'scripts/button_only_training.py',ROOT/'scripts/train_navigation_buttons.py',ROOT/'scripts/evaluate_sword_buttons.py',ROOT/'scripts/audit_sword_buttons.py',ROOT/'tests/test_button_only_training.py']
    plan.update(status='frozen_untrained',training_performed=False,ablation='Only train output rows 5:8. Shared layers and movement rows 0:5 remain byte-identical to selected v7; Adam without weight decay, masked gradients, assertion after every step.',
        prior_plan_sha256=sha256(prior/'plan.json'),prior_result_sha256=sha256(prior/'result.json'),
        button_helper_sha256=sha256(ROOT/'scripts/button_only_training.py'),trainer_sha256=sha256(ROOT/'scripts/train_navigation_buttons.py'),freeze_source_sha256=sha256(__file__),
        frozen_sources={str(p.relative_to(ROOT)):sha256(p) for p in sources},
        note='All data, loss weights, seed, batches, LR, eight epochs, final-checkpoint rule and evaluation gates match v1. Freezing movement does not preserve trajectories when buttons change timing or terrain.')
    (out/'plan.json').write_text(json.dumps(plan,indent=2))
    for p in sources:shutil.copy2(p,out/p.name)
    print('FROZEN',sha256(out/'plan.json'))
if __name__=='__main__':main()
