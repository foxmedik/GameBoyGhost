"""Extract bounded, first-trigger teacher spans for the standalone recovery skill."""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
import numpy as np
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.room15_model_v4 import action_index, temporal_feature, update
from collect_room15_overnight import prefix, senses
from run_toadstool_progression import apply


def norm(v): return json.loads(json.dumps(v))


def main():
    p=argparse.ArgumentParser(); p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    plan=json.loads(a.plan.read_text()); source=ROOT/'runs/state-driven-tail-cave-disengage-guarded-v1'; guided=ROOT/'runs/room15-v5-guided-30m'; teacher=ROOT/plan['source']
    summary=json.loads((teacher/'summary.json').read_text())
    if summary['successes'] != plan['required_skill_successes'] or summary['exact_replays'] != plan['required_exact_replays']: raise RuntimeError('Teacher source gate incomplete')
    rows=[]; provenance=[]
    for result in summary['results']:
        spec=result['spec']; case=spec['id']; guided_id='guided-v5-'+case.split('-')[1]
        guided_rows=[json.loads(x) for x in (guided/guided_id/'trajectory.jsonl').read_text().splitlines()]
        events=json.loads((guided/guided_id/'evidence.json').read_text()); hit=next(x for x in events if x['kind']=='guided_early_y80_recovery')
        prefix_rows=[r for r in guided_rows if r['frame'] < hit['frame']]
        teacher_rows=[json.loads(x) for x in (teacher/case/'trajectory.jsonl').read_text().splitlines()]
        x0,y0=teacher_rows[0]['before']['x'],teacher_rows[0]['before']['y']; limit=next(i+1 for i,r in enumerate(teacher_rows) if abs(r['after']['x']-x0)+abs(r['after']['y']-y0)>=16)
        env=ProgressionEnv(source/f"development-house-{spec['base']:02d}"/'game.gbc',source/f"development-house-{spec['base']:02d}"/'initial.state',max_steps=16000,max_frames=300000,completion_milestone=None); history=[]
        try:
            env.reset(seed=0);prefix(env,source/f"development-house-{spec['base']:02d}");env.step_input_events(release=('up','down','left','right','a','b','start','select'),frames=spec['idle'])
            for r in prefix_rows:
                before=norm(snapshot(env.pyboy)); action=action_index(r['command']);info=apply(env,r['command'])[4];after=norm(snapshot(env.pyboy))
                if fingerprint(env)!=r['fingerprint'] or after!=norm(r['after']) or info['events']!=r['events']:raise RuntimeError(f'prefix mismatch {case}')
                if action is not None: history=update(history,action,before,after)
            for i,r in enumerate(teacher_rows[:limit]):
                action=action_index(r['command']);
                if action is None:raise RuntimeError(f'unsupported teacher action {case}/{i}')
                rows.append((temporal_feature(senses(env),history),action));provenance.append([case,i])
                before=norm(snapshot(env.pyboy));info=apply(env,r['command'])[4];after=norm(snapshot(env.pyboy))
                if fingerprint(env)!=r['fingerprint'] or after!=norm(r['after']) or info['events']!=r['events']:raise RuntimeError(f'teacher mismatch {case}/{i}')
                history=update(history,action,before,after)
        finally: env.close()
    a.out.mkdir(parents=True,exist_ok=False);np.savez_compressed(a.out/'skill.npz',x=np.stack([r[0] for r in rows]),y=np.asarray([r[1] for r in rows]),provenance=np.asarray(provenance))
    report={'rows':len(rows),'episodes':len(summary['results']),'validation_loaded':False,'training_started':False};(a.out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
