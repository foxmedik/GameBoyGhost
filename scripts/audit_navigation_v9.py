"""Read all paired local/route regressions of the fixed learned candidate."""
import json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runs/navigation-routes-v9'
read=lambda p:json.loads(p.read_text())

def main():
 report=read(OUT/'result.json');details=[]
 for panel,summary in report['local_panels'].items():
  for r in summary['episodes']:
   old=read(ROOT/f"runs/navigation-routes-v7/eval-{panel}/{r['case_id']}-learned.json")
   if r['case_id'] not in summary['lost'] and r['damage']<=old['damage'] and r['status']!='death':continue
   now=read(OUT/f"eval-{panel}/{r['case_id']}-candidate.json")
   i=next((i for i,(a,b) in enumerate(zip(old['actions'],now['actions'])) if a!=b),None)
   positions=Counter((tuple(e['state']['room']),e['state']['x'],e['state']['y']) for e in now['events'])
   def compact(e):return {k:e[k] for k in ('step','state','after_state','action','damage')} | {'entities':e['inputs']['entities']}
   details.append(dict(panel=panel,case_id=r['case_id'],baseline_success=old['success'],candidate_success=r['success'],damage_delta=r['damage']-old['damage'],first_action_divergence=i,baseline_final=dict(room=old['final_room'],x=old['final_x'],y=old['final_y']),candidate_final=now['final_state'],repeated_positions=[dict(room=k[0],x=k[1],y=k[2],actions=v) for k,v in positions.most_common(3)],divergence_window=[compact(e) for e in now['events'][max(0,(i or 0)-1):(i or 0)+4]],final_window=[compact(e) for e in now['events'][-4:]],damage_windows=[[compact(e) for e in now['events'][max(0,j-3):j+2]] for j,e in enumerate(now['events']) if e['damage']]))
 routes=[r for r in report['routes'] if r['lost'] or r['waypoints_lost'] or r['damage'] or r['status']=='death']
 for r in routes:
  root=OUT/'candidate'/f"{r['route']}-{r['start']}";b=read(root/'result.json');a=read(ROOT/f"runs/navigation-routes-v7/candidate/{root.name}/result.json")
  i=next((i for i,(x,y) in enumerate(zip(a['actions'],b['actions'])) if x!=y),None)
  t=[json.loads(x) for x in (root/'trajectory.jsonl').read_text().splitlines()];counts=Counter((tuple(e['room']),e['x'],e['y']) for e in t if e['skill']=='navigation')
  r.update(first_divergence=i,baseline_action=a['actions'][i] if i is not None else None,candidate_action=b['actions'][i] if i is not None else None,final_state=b['final_state'],final_window=t[-4:],repeated_positions=[dict(room=k[0],x=k[1],y=k[2],actions=v) for k,v in counts.most_common(3)])
 result=dict(local_regressions=details,route_regressions=routes,training_fit=read(OUT/'training-fit-diagnostic.json'),interpretation='Descriptive trace audit; first divergence or repeated position does not establish the cause of failure.')
 (OUT/'audit.json').write_text(json.dumps(result,indent=2));(ROOT/'reports/navigation-routes-v9-audit.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(dict(local=[{k:r[k] for k in ('panel','case_id','damage_delta','first_action_divergence','repeated_positions')} for r in details],routes=routes),indent=2))
if __name__=='__main__':main()
