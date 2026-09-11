"""Audit each regression and source-derived cutting predictions after frozen v2."""
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/proximity-sword-48-v2'

def main():
    report=json.loads((OUT/'result.json').read_text())
    cases={c['segment_id']:c for c in json.loads((OUT/'plan.json').read_text())['cases']}
    audits=[];terrain=Counter();examples=[]
    for variant in ('terrain','terrain_motion'):
        for key,case in cases.items():
            r=json.loads((OUT/f'{key}-{variant}.json').read_text())
            for i,e in enumerate(r['events']):
                if e['reason']!='reachable_foliage':continue
                terrain[variant+'_allowed']+=1
                target=e['terrain_target'];changed=False
                for later in r['events'][i+1:i+4]:
                    if later['state']['room']!=e['state']['room']:break
                    if later['inputs']['objects'][target['index']]!=target['object_id']:
                        changed=True;break
                terrain[variant+('_changed_within_3_actions' if changed else '_not_confirmed')]+=1
                if changed and len(examples)<12:
                    examples.append(dict(case_id=key,variant=variant,step=i,before=e['state'],target=target,after_object_id=later['inputs']['objects'][target['index']]))
            pair=next(p for p in report['pairs'] if p['case_id']==key and p['variant']==variant)
            if not (pair['lost'] or pair['damage_delta']>0 or pair['new_death']):continue
            a=json.loads((OUT/f'{key}-cadence.json').read_text())
            divergence=next((i for i,(x,y) in enumerate(zip(a['actions'],r['actions'])) if x!=y),None)
            def compress(e):
                return {k:e[k] for k in ('step','state','after_state','proposed','action','reason','damage','terrain_target')} | {'entities':e['inputs']['entities']}
            frequent=Counter((tuple(e['state']['room']),e['state']['x'],e['state']['y']) for e in r['events'])
            audit=dict(**pair,goal=case['goal'],first_divergence=divergence,
                baseline_status=a['status'],variant_status=r['status'],baseline_final=a['final_state'],variant_final=r['final_state'],
                repeated_positions=[dict(room=room,x=x,y=y,actions=n) for (room,x,y),n in frequent.most_common(3)],
                divergence_window=[compress(e) for e in r['events'][max(0,(divergence or 0)-1):(divergence or 0)+3]],
                final_window=[compress(e) for e in r['events'][-4:]],
                damage_windows={v:[[compress(e) for e in rr['events'][max(0,i-3):i+2]] for i,ev in enumerate(rr['events']) if ev['damage']] for v,rr in [('cadence',a),(variant,r)]})
            audits.append(audit)
    result=dict(regressions=audits,terrain_observations=dict(terrain),cut_examples=examples,
                caveat='A target change within three actions verifies a local terrain outcome, not all sword geometry or sole causation. Windows may overlap.')
    (OUT/'audit.json').write_text(json.dumps(result,indent=2))
    (ROOT/'reports/proximity-sword-48-v2-audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(terrain_observations=dict(terrain),regressions=[{k:a[k] for k in ('case_id','variant','lost','damage_delta','goal','variant_final','repeated_positions')} for a in audits]),indent=2))
if __name__=='__main__':main()
