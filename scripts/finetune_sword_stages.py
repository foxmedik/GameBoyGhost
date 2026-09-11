"""Explicit weight-transfer stages; each stage has a fresh resumable PPO run."""
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sword_imitation import STARTS,write

def main():
    out=Path(sys.argv[1]);policy=Path(sys.argv[2]).resolve()
    records=[]
    for name,steps in [('approach',8192),('beach',16384),('house',32768)]:
        command=[sys.executable,str(ROOT/'scripts/train_ladx.py'),'--steps',str(steps),
                 '--initial-state',str(STARTS[name]),'--sword-curriculum','--warm-start',str(policy),
                 '--checkpoint-every','8192']
        with (out/f'finetune-{name}.log').open('x') as f:
            subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1800)
        lines=(out/f'finetune-{name}.log').read_text().splitlines()
        run=Path(next(x[4:] for x in lines if x.startswith('RUN ')))
        state=json.loads((run/'result.json').read_text());checkpoint=Path(state['latest_checkpoint'])
        policy=checkpoint/'policy.zip'
        records.append({'stage':name,'steps':steps,'run':str(run),'checkpoint':str(checkpoint),
                        'sword_successes':state.get('sword_successes',0),'episodes':state['episodes_completed'],
                        'deaths':state['deaths'],'weight_transfer':state['weight_transfer']})
        write(out/'finetune-stages.json',records)
        print(json.dumps(records[-1]),flush=True)
    with (out/'finetune-evaluation.log').open('x') as f:
        subprocess.run([sys.executable,str(ROOT/'scripts/sword_imitation.py'),'evaluate','--out',str(out),
                        '--policy',str(policy),'--tag','bc-plus-ppo'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
if __name__=='__main__':main()
