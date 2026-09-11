"""Inspect every lost success or damage increase in the v7 teacher diagnostic."""
import json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runs/v7-sword-teacher-v1'
read=lambda p:json.loads(p.read_text())

def main():
 report=read(OUT/'result.json');cases={c['segment_id']:c for c in read(OUT/'plan.json')['cases']};audits=[]
 for p in report['pairs']:
  if not(p['lost'] or p['damage_delta']>0 or p['new_death']):continue
  key=p['case_id'];a=read(OUT/f'{key}-v7.json');b=read(OUT/f'{key}-v7_gated.json')
  i=next((i for i,(x,y) in enumerate(zip(a['actions'],b['actions'])) if x!=y),None)
  counts=Counter((tuple(e['state']['room']),e['state']['x'],e['state']['y']) for e in b['events'])
  compact=lambda e:{k:e[k] for k in ('step','state','after_state','proposed','action','reason','damage','terrain_target')} | {'entities':e['inputs']['entities']}
  audits.append(dict(**p,goal=cases[key]['goal'],baseline_status=a['status'],gated_status=b['status'],baseline_final=a['final_state'],gated_final=b['final_state'],first_divergence=i,
    baseline_action=a['actions'][i] if i is not None else None,gated_action=b['actions'][i] if i is not None else None,
    divergence_window=[compact(e) for e in b['events'][max(0,(i or 0)-1):(i or 0)+4]],
    repeated_positions=[dict(room=k[0],x=k[1],y=k[2],actions=v) for k,v in counts.most_common(3)],
    final_window=[compact(e) for e in b['events'][-4:]],
    damage_windows={v:[[compact(e) for e in r['events'][max(0,j-3):j+2]] for j,e in enumerate(r['events']) if e['damage']] for v,r in [('v7',a),('v7_gated',b)]}))
 result=dict(regressions=audits,interpretation='All regression cases inspected; first divergence and repeated positions are descriptive evidence, not a unique causal attribution.')
 for path in [OUT/'audit.json',ROOT/'reports/v7-sword-teacher-v1-audit.json']:path.write_text(json.dumps(result,indent=2))
 print(json.dumps([{k:r[k] for k in ('case_id','lost','damage_delta','first_divergence','baseline_action','gated_action','repeated_positions')} for r in audits],indent=2))
if __name__=='__main__':main()
