"""Collect guarded corrections on the failed v4 autonomous timing panel."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import torch
from gameboy_agent.world_memory import file_hash
from collect_tail_cave_integration_dagger_v4 import run_variant
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/'configs/tail_cave_integration_dagger_v5_collection.json'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main(out):
 plan=json.loads(PLAN.read_text());entry=ROOT/plan['entry_states'];source_root=ROOT/plan['source_run']
 for path,key in ((Path(__file__),'collector_sha256'),(ROOT/plan['shared_collector_source'],'shared_collector_source_sha256'),(ROOT/plan['candidate'],'candidate_sha256'),(ROOT/plan['feature_source'],'feature_source_sha256'),(ROOT/plan['teacher_source'],'teacher_source_sha256'),(ROOT/plan['failed_evaluation'],'failed_evaluation_sha256')):
  if file_hash(path)!=plan[key]:raise ValueError(f'Frozen input changed: {path}')
 saved=torch.load(ROOT/plan['candidate'],map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);model.eval();out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');results=[]
 for base_id in plan['base_case_ids']:
  meta=json.loads((entry/f'{base_id:02d}.json').read_text());state=entry/f'{base_id:02d}.state'
  if file_hash(state)!=meta['state_sha256']:raise ValueError(f'Entry state changed: {state}')
  source=source_root/f'development-house-{base_id:02d}'
  for idle in plan['idle_frames']:
   result=run_variant(out,base_id,idle,source/'game.gbc',state,meta['history'],model,saved,plan);results.append(result)
   write(out/'summary.json',{'cases':len(results),'successes':sum(r['success'] for r in results),'required_successes':plan['required_successes'],'correction_rows':sum(r['correction_rows'] for r in results if r['success']),'results':results,'validation_loaded':False})
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
