"""Derive exact v5 route arrivals, then collect on-policy teacher labels."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import torch
from gameboy_agent.world_memory import file_hash
from collect_tail_cave_integration_dagger_v4 import derive_entry
from collect_tail_cave_on_policy_dagger_v6 import run_case
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/'configs/tail_cave_exact_route_dagger_v7_collection.json'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main(out):
 plan=json.loads(PLAN.read_text())
 for path,key in ((Path(__file__),'collector_sha256'),(ROOT/plan['candidate'],'candidate_sha256'),(ROOT/plan['shared_on_policy_source'],'shared_on_policy_source_sha256'),(ROOT/plan['shared_derivation_source'],'shared_derivation_source_sha256'),(ROOT/plan['source_run']/'summary.json','source_summary_sha256')):
  if file_hash(path)!=plan[key]:raise ValueError(f'Frozen input changed: {path}')
 out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/'plan.json');entries=out/'entries';entries.mkdir()
 source_root=ROOT/plan['source_run']
 for base_id in plan['base_case_ids']:
  source=source_root/f'development-house-{base_id:02d}';state_path=entries/f'{base_id:02d}.state';history,state,spec=derive_entry(source,state_path);write(entries/f'{base_id:02d}.json',{'history':history,'state':state,'spec':spec,'state_sha256':file_hash(state_path)})
 saved=torch.load(ROOT/plan['candidate'],map_location='cpu');model=DaggerNet(saved['inputs']);model.load_state_dict(saved['model']);model.eval();results=[]
 for base_id in plan['base_case_ids']:
  for idle in plan['idle_frames']:
   results.append(run_case(out,base_id,idle,plan,model,saved));write(out/'summary.json',{'cases':len(results),'successes':sum(r['success'] for r in results),'required_successes':plan['required_successes'],'correction_rows':sum(r['correction_rows'] for r in results if r['success']),'candidate_steps':sum(r['candidate_steps'] for r in results),'teacher_recoveries':sum(r['teacher_recovery'] is not None for r in results),'results':results,'validation_loaded':False})
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
