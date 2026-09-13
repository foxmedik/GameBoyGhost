"""Launch focused fine-tuning on continuous shield-disengagement labels."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from gameboy_agent.world_memory import file_hash
import train_tail_cave_integration_dagger_v4 as trainer
PLAN=ROOT/'configs/tail_cave_disengage_v10_training.json'
def main(out):
 plan=json.loads(PLAN.read_text())
 if file_hash(Path(__file__))!=plan['launcher_sha256']:raise ValueError('Frozen launcher changed')
 trainer.PLAN=PLAN;trainer.main(out)
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
