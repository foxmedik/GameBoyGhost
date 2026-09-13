"""Dispatch frozen candidate 3 through the candidate-2 verified trainer."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import train_progression_local_control_v2 as trainer


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    trainer.CONFIG = ROOT / "configs/progression_local_control_v3.json"
    trainer.run(args.out)
