"""Freeze and execute the unchanged full-route guided teacher panel, stopping on rejection."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from house_door_teacher import MODELS
from gameboy_agent.world_memory import file_hash


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True)
    p.add_argument('--development-proof',nargs='+',default=['runs/teacher-fresh-house-probe-v12/summary.json'])
    p.add_argument('--recovery-proof',default='runs/teacher-physical-half-heart-probe-v1/summary.json')
    p.add_argument('--jobs',type=int,choices=(1,2,4),default=1)
    a=p.parse_args()
    out=ROOT/a.output;out.mkdir(parents=True,exist_ok=False)
    panel_path=ROOT/'configs/house_boss_door_teacher_panel_v1.json'
    panel_hash=file_hash(panel_path)
    if panel_hash!='f224acd2aeb6fe4661d7b5cf57de0cb9e8993b2e57a16e331928dda701f38c01':
        raise RuntimeError('Panel no longer matches its original frozen hash')
    panel=json.loads(panel_path.read_text())
    paths=sorted((ROOT/'src/gameboy_agent').glob('*.py'))+sorted((ROOT/'scripts').glob('*.py'))
    paths+=sorted((ROOT/'configs').glob('*.json'))+[ROOT/v for v in MODELS.values()]
    for config in ('sword_controller.json','navigation_experiment.json'):
        value=json.loads((ROOT/'configs'/config).read_text())
        if value.get('policy_path'):paths.append(ROOT/value['policy_path'])
    binding={str(v.relative_to(ROOT)):file_hash(v) for v in paths}
    for name,digest in panel['start_hashes'].items():
        if file_hash(ROOT/name)!=digest:raise RuntimeError('Frozen start artifact changed')
    candidate=dict(schema='house-door-teacher-candidate-binding-v1',panel=str(panel_path.relative_to(ROOT)),
        panel_sha256=panel_hash,binding=binding,start_hashes=panel['start_hashes'],
        python=platform.python_version(),dependencies={v:importlib.metadata.version(v) for v in ('pyboy','torch','numpy')},
        control='guided',training_eligible=False,stop_after_failed_batch=True,parallel_cases=a.jobs,
        prerequisites=[*a.development_proof,a.recovery_proof])
    for path in candidate['prerequisites']:
        result=json.loads((ROOT/path).read_text())
        if not result['success'] or not result['exact_replay']:raise RuntimeError('Development prerequisite failed')
    candidate['prerequisite_hashes']={path:file_hash(ROOT/path) for path in candidate['prerequisites']}
    binding_path=out/'candidate-binding.json';write(binding_path,candidate)
    binding_hash=file_hash(binding_path);(out/'candidate-binding.sha256').write_text(binding_hash+'\n')
    result=dict(schema='house-door-teacher-qualification-result-v1',status='running',qualified=False,
        candidate_binding_sha256=binding_hash,panel_sha256=panel_hash,cases=[],house_passed=0,recovery_passed=0,
        training_eligible=False,labels_generated=0)
    write(out/'result.json',result)
    def run_case(case):
        case_out=out/case['id']
        cmd=[sys.executable,str(ROOT/'scripts/develop_house_door_teacher.py'),'--output',str(case_out.relative_to(ROOT)),
             '--idle',str(case['house_idle_frames']),'--qualification-binding',str(binding_path.relative_to(ROOT)),
             '--binding-sha256',binding_hash,'--case-id',case['id'],'--hypothesis','Frozen qualification case; no controller edits or rescue']
        if case['kind']=='recovery':cmd.append('--recovery')
        print('QUALIFICATION CASE '+case['id'],flush=True)
        error=None
        with (out/(case['id']+'.log')).open('x') as log:
            try:
                completed=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=case['max_wall_seconds'])
                if completed.returncode:error='Harness process exit '+str(completed.returncode)
            except subprocess.TimeoutExpired:error='Frozen case wall budget exhausted including replay'
        summary_path=case_out/'summary.json'
        summary=json.loads(summary_path.read_text()) if summary_path.exists() else {}
        passed=error is None and summary.get('success') and summary.get('exact_replay') and summary.get('qualification')
        unchanged=(file_hash(binding_path)==binding_hash and all(file_hash(ROOT/name)==digest for name,digest in binding.items()))
        passed=bool(passed and unchanged)
        row=dict(id=case['id'],kind=case['kind'],passed=passed,error=error or summary.get('failure'),binding_unchanged=unchanged,
                 summary=str(summary_path.relative_to(ROOT)),summary_sha256=file_hash(summary_path) if summary_path.exists() else None)
        return row
    for offset in range(0,len(panel['cases']),a.jobs):
        batch=panel['cases'][offset:offset+a.jobs]
        with ThreadPoolExecutor(max_workers=a.jobs) as pool:
            rows=list(pool.map(run_case,batch))
        for row in rows:
            result['cases'].append(row)
            if row['passed']:result['house_passed' if row['kind']=='house' else 'recovery_passed']+=1
            else:result['status']='rejected'
            write(out/'result.json',result)
            print(json.dumps(row),flush=True)
        if any(not row['passed'] for row in rows):break
    result['qualified']=result['house_passed']==20 and result['recovery_passed']==4
    result['status']='qualified' if result['qualified'] else 'rejected'
    result['not_run']=[c['id'] for c in panel['cases'] if c['id'] not in {r['id'] for r in result['cases']}]
    write(out/'result.json',result)
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
