"""Build v3 data with observed action outcomes, not action history alone."""
import argparse,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.room15_model import action_index
from gameboy_agent.room15_model_v3 import temporal_feature,update
from gameboy_agent.world_memory import file_hash
from collect_room15_overnight import prefix,senses
from run_toadstool_progression import apply

def normalized(value):return json.loads(json.dumps(value))
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')

def clean_rows(labels,cases):
    result=[]
    for case in cases:
        rows=sorted((r for r in labels if r['case_id']==case),key=lambda r:r['command_index']);history=[]
        for index,row in enumerate(rows):
            action=action_index(row['command'])
            if action is None:continue
            result.append((temporal_feature(row['observation'],history),action,[case,row['command_index']]))
            after=rows[index+1]['observation']['state'] if index+1<len(rows) else row['observation']['state']
            history=update(history,action,row['observation']['state'],after)
    return result

def correction_rows(plan):
    result=[];correction=ROOT/plan['corrections'];summary=json.loads((correction/'summary.json').read_text())
    for item in summary['results']:
        if not item['success'] or not item['exact_replay']:raise RuntimeError('Nonexact correction')
        spec=item['spec'];case=correction/spec['id'];source=ROOT/plan['source']/f"development-house-{spec['base']:02d}";student=ROOT/plan['student_gate']/spec['student_case']
        student_rows=[json.loads(line) for line in (student/'trajectory.jsonl').read_text().splitlines()];teacher_rows=[json.loads(line) for line in (case/'trajectory.jsonl').read_text().splitlines()]
        env=ProgressionEnv(source/'game.gbc',source/'initial.state',max_steps=16000,max_frames=300000,completion_milestone=None);history=[]
        try:
            env.reset(seed=0);prefix(env,source);env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['idle'])
            for row in student_rows:
                before=normalized(snapshot(env.pyboy));action=action_index(row['command']);info=apply(env,row['command'])[4];after=normalized(snapshot(env.pyboy))
                if fingerprint(env)!=row['fingerprint'] or after!=normalized(row['after']) or env.frames!=row['frame'] or info['events']!=row['events']:raise RuntimeError('Student replay mismatch')
                if action is not None:history=update(history,action,before,after)
            for row in teacher_rows:
                before=normalized(snapshot(env.pyboy));action=action_index(row['command'])
                if action is not None:result.append((temporal_feature(senses(env),history),action,[spec['id'],row['decision']]))
                info=apply(env,row['command'])[4];after=normalized(snapshot(env.pyboy))
                if fingerprint(env)!=row['fingerprint'] or after!=normalized(row['after']) or env.frames!=row['frame'] or info['events']!=row['events']:raise RuntimeError('Teacher replay mismatch')
                if action is not None:history=update(history,action,before,after)
        finally:env.close()
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();plan=json.loads(args.plan.read_text())
    if file_hash(Path(__file__))!=plan['extractor_sha256']:raise RuntimeError('Frozen extractor changed')
    manifest=ROOT/plan['labels_manifest'];labels_info=json.loads(manifest.read_text())
    if file_hash(manifest)!=plan['labels_manifest_sha256'] or labels_info['validation_loaded']:raise RuntimeError('Label source changed')
    correction=ROOT/plan['corrections'];summary=correction/'summary.json'
    if file_hash(summary)!=plan['corrections_summary_sha256']:raise RuntimeError('Correction source changed')
    labels=[json.loads(line) for line in (manifest.parent/'labels.jsonl').read_text().splitlines()];splits={'train':clean_rows(labels,plan['train_cases'])+correction_rows(plan),'development':clean_rows(labels,plan['development_cases'])}
    args.out.mkdir(parents=True,exist_ok=False);shutil.copy2(args.plan,args.out/'plan.json');out={'schema':'room15-student-data-v3','experiment_sha256':file_hash(args.plan),'validation_loaded':False,'splits':{}}
    for name,rows in splits.items():
        x=np.stack([r[0] for r in rows]);y=np.asarray([r[1] for r in rows],dtype=np.int64);p=np.asarray([r[2] for r in rows]);path=args.out/f'{name}.npz';np.savez_compressed(path,x=x,y=y,provenance=p);out['splits'][name]={'rows':len(rows),'sha256':file_hash(path),'correction_rows':sum(str(r[2][0]).startswith('correction-') for r in rows)}
    write(args.out/'manifest.json',out);print(json.dumps(out,indent=2))
if __name__=='__main__':main()
