"""Replay selected paired failures and capture physical diagnostic states."""
import sys,json,shutil,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import pyarrow.parquet as pq
from gameboy_agent.training_env import TrainingEnv
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.dataset import sha256
from control_context import ControlContext
from run_skill_chain import senses
from proximity_sword import inputs
OUT=ROOT/'runs/proximity-sword-48-v1'

def inspect(key):
 plan=json.loads((OUT/'plan.json').read_text());case=next(c for c in plan['cases'] if c['segment_id']==key);batch=ROOT/'runs/data-workset-16m-v1';source=batch/case['source_path'];assert sha256(source)==case['source_sha256'];meta=json.loads((source.parent/'manifest.json').read_text());prefix=pq.read_table(source,columns=['action']).to_pydict()['action'][:case['step']]
 a=json.loads((OUT/f'{key}-cadence.json').read_text());b=json.loads((OUT/f'{key}-proximity.json').read_text());first=next(i for i,(x,y) in enumerate(zip(a['actions'],b['actions'])) if x!=y);report=dict(case=case,first_divergence=first)
 dest=OUT/'diagnostics';dest.mkdir(exist_ok=True)
 for variant,r in [('cadence',a),('proximity',b)]:
  with tempfile.TemporaryDirectory() as tmp:
   rom=Path(tmp)/'game.gbc';shutil.copy2(batch/'assets/game.gbc',rom);base=TrainingEnv(rom,batch/'assets'/f'{case["start"]}.state',max_steps=meta['max_steps'],sword_curriculum=False);env=ControlContext(base)
   try:
    env.reset(seed=meta['seed'])
    for action in prefix:env.step(np.asarray(action))
    base.config['max_steps']=base.total_steps+129;assert fingerprint(base)==r['start_fingerprint']
    for i,action in enumerate(r['actions']):
     if i==first:
      base.pyboy.screen.image.save(dest/f'{key}-{variant}-divergence.png');report[variant]=dict(state=senses(base).__dict__,inputs=inputs(base),action=action)
     env.step(np.asarray(action))
    assert fingerprint(base)==r['final_fingerprint'];base.pyboy.screen.image.save(dest/f'{key}-{variant}-final.png')
   finally:env.close()
 (dest/f'{key}.json').write_text(json.dumps(report,indent=2));print(key,first,flush=True)
if __name__=='__main__':
 for key in sys.argv[1:]:inspect(key)
