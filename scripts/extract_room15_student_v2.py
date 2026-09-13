"""Add exact teacher recoveries to the frozen v1 room-15 training split."""
import argparse, json, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.room15_model import action_index,feature
from gameboy_agent.world_memory import file_hash
from collect_room15_overnight import prefix,senses
from run_toadstool_progression import apply


def normalized(value):return json.loads(json.dumps(value))
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();plan=json.loads(args.plan.read_text())
    if file_hash(Path(__file__))!=plan['extractor_sha256']:raise RuntimeError('Frozen extractor changed')
    v1=ROOT/plan['v1_data'];v1_manifest=json.loads((v1/'manifest.json').read_text())
    if file_hash(v1/'manifest.json')!=plan['v1_manifest_sha256'] or v1_manifest['validation_loaded']:raise RuntimeError('Frozen v1 data changed')
    correction=ROOT/plan['corrections'];summary=json.loads((correction/'summary.json').read_text())
    if file_hash(correction/'summary.json')!=plan['corrections_summary_sha256'] or summary['successes']!=summary['cases'] or summary['validation_loaded']:raise RuntimeError('Correction collection changed or failed')
    train=np.load(v1/'train.npz');development=np.load(v1/'development.npz'); xs=[train['x']];ys=[train['y']];provenance=[train['provenance']]
    for result in summary['results']:
        if not result['success'] or not result['exact_replay']:raise RuntimeError('Nonexact correction')
        spec=result['spec'];case=correction/spec['id'];source=ROOT/plan['source']/f"development-house-{spec['base']:02d}";student=ROOT/plan['student_gate']/spec['student_case'];m=json.loads((case/'manifest.json').read_text())
        for name,digest in m.items():
            if file_hash(case/name)!=digest:raise RuntimeError(f'Correction artifact changed: {case/name}')
        student_rows=[json.loads(line) for line in (student/'trajectory.jsonl').read_text().splitlines()];teacher_rows=[json.loads(line) for line in (case/'trajectory.jsonl').read_text().splitlines()]
        env=ProgressionEnv(source/'game.gbc',source/'initial.state',max_steps=16000,max_frames=300000,completion_milestone=None);history=[]
        try:
            env.reset(seed=0);prefix(env,source);env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['idle'])
            for row in student_rows:
                action=action_index(row['command']);
                if action is not None:history.append(action)
                info=apply(env,row['command'])[4]
                if fingerprint(env)!=row['fingerprint'] or normalized(snapshot(env.pyboy))!=normalized(row['after']) or env.frames!=row['frame'] or info['events']!=row['events']:raise RuntimeError('Student replay mismatch')
            x,y,p=[],[],[]
            for row in teacher_rows:
                action=action_index(row['command'])
                if action is not None:
                    x.append(feature(senses(env),history));y.append(action);p.append([spec['id'],row['decision']]);history.append(action)
                info=apply(env,row['command'])[4]
                if fingerprint(env)!=row['fingerprint'] or normalized(snapshot(env.pyboy))!=normalized(row['after']) or env.frames!=row['frame'] or info['events']!=row['events']:raise RuntimeError('Teacher replay mismatch')
            xs.append(np.stack(x));ys.append(np.asarray(y,dtype=np.int64));provenance.append(np.asarray(p))
        finally:env.close()
    args.out.mkdir(parents=True,exist_ok=False);shutil.copy2(args.plan,args.out/'plan.json');np.savez_compressed(args.out/'train.npz',x=np.concatenate(xs),y=np.concatenate(ys),provenance=np.concatenate(provenance));shutil.copy2(v1/'development.npz',args.out/'development.npz')
    manifest=dict(schema='room15-student-data-v2',experiment_sha256=file_hash(args.plan),validation_loaded=False,splits={'train':{'rows':len(np.concatenate(ys)),'sha256':file_hash(args.out/'train.npz'),'includes_correction_rows':sum(len(v) for v in ys[1:])},'development':{'rows':len(development['y']),'sha256':file_hash(args.out/'development.npz')}})
    write(args.out/'manifest.json',manifest);print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
