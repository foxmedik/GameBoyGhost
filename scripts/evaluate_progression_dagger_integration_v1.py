"""Candidate room-52 crossing followed by physical mushroom acquisition."""
import argparse,json,shutil,sys,time
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"scripts"))
import torch
from control_context import ControlContext
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.toadstool_teacher import execute as mushroom
from gameboy_agent.world_memory import file_hash
from collect_progression_dagger_v1 import DURATIONS,buttons,feature,frozen_goal
from progression_local_control import json_state
from run_toadstool_progression import Trace,apply
from train_progression_dagger_v1 import DaggerNet
PLAN=ROOT/"configs/progression_dagger_v1_integration.json"
def write(p,v):p.write_text(json.dumps(v,indent=2)+"\n")

def run_case(root,spec,plan,model,saved):
 source=ROOT/plan["source_teacher"]/spec["source_case"];out=root/spec["id"];out.mkdir(parents=True,exist_ok=False)
 for n in ("game.gbc","initial.state"):shutil.copy2(source/n,out/n)
 m=json.loads((source/"manifest.json").read_text())
 for n,w in m["artifacts"].items():
  if file_hash(source/n)!=w:raise ValueError(f"Source changed: {source/n}")
 old=[json.loads(x) for x in (source/"trajectory.jsonl").read_text().splitlines()]
 start=next(i for i,r in enumerate(old) if r["before"]["room"]==[0,0,0x52] and not r["before"]["toadstool"] and not r["before"]["powder"])
 base=ProgressionEnv(out/"game.gbc",out/"initial.state",max_steps=12288,max_frames=300000);rows=[];failure=None;candidate_steps=0;began=time.monotonic()
 with (out/"trajectory.jsonl").open("x") as stream:
  env=Trace(base,stream,rows)
  try:
   base.reset(seed=0)
   for r in old[:start]:apply(env,r["command"]);assert rows[-1]["fingerprint"]==r["fingerprint"]
   env.step_input_events(release=("up","down","left","right","a","b","start","select"),frames=spec["arrival_idle_frames"])
   def learned_crossing(traced,evidence):
    nonlocal candidate_steps
    goal=frozen_goal(base);context=ControlContext(base);previous=None;stationary=0;recoveries=0
    for _ in range(plan["decision_budget"]):
     state=json_state(snapshot(base.pyboy))
     if state["room"]==[0,0,0x62]:evidence.append({"kind":"learned_forest_crossing","frame":base.frames,"decisions":candidate_steps});return
     if state["room"]!=[0,0,0x52] or not state["health"]:raise RuntimeError(f"Learned crossing left valid state: {state['room']}")
     raw=feature(base,context,state,goal);x=torch.from_numpy(raw.copy());n=saved["base_inputs"]
     x[:n]=(x[:n]-torch.from_numpy(saved["mean"]))/torch.from_numpy(saved["scale"])*torch.from_numpy(saved["input_mask"])
     with torch.no_grad():z=model(x)
     action=[int(z[:5].argmax()),int(z[5:8].argmax()),int(z[8:].argmax())]
     traced.step_buttons(buttons(action),action_frames=DURATIONS[action[2]],legacy_action=action[:2]);candidate_steps+=1
     now=json_state(snapshot(base.pyboy));pose=(now["x"],now["y"]);stationary=stationary+1 if pose==previous else 0;previous=pose
     if stationary>=12:
      if recoveries>=4:raise RuntimeError(f"Learned crossing stalled at {pose}")
      traced.step_buttons([("left","right","up","down")[recoveries],"b"],action_frames=3);recoveries+=1;stationary=0
    raise RuntimeError("Learned crossing budget exhausted")
   evidence=[];mushroom(env,evidence,forest_crossing=learned_crossing)
   final=json_state(snapshot(base.pyboy))
   if not final["toadstool"] or "toadstool_acquired" not in base.journal.milestones:raise RuntimeError("Following mushroom interaction failed")
  except Exception as exc:failure=f"{type(exc).__name__}: {exc}"
  finally:final=json_state(snapshot(base.pyboy));journal=deepcopy(base.journal.state());base.close()
 replay=ProgressionEnv(out/"game.gbc",out/"initial.state",max_steps=12288,max_frames=300000)
 try:
  replay.reset(seed=0)
  for r in rows:
   info=apply(replay,r["command"])[4];assert fingerprint(replay)==r["fingerprint"];assert json_state(snapshot(replay.pyboy))==json_state(r["after"]);assert replay.frames==r["frame"] and info["events"]==r["events"]
  assert replay.journal.state()==journal
 finally:replay.close()
 result={"spec":spec,"success":failure is None,"failure":failure,"candidate_decisions":candidate_steps,"final":final,"exact_replay":True,
  "damage_raw":journal["damage_raw"],"healing_raw":journal["healing_raw"],"seconds":round(time.monotonic()-began,3)}
 write(out/"result.json",result);write(out/"manifest.json",{"artifacts":{p.name:file_hash(p) for p in out.iterdir() if p.is_file() and p.name!="game.gbc"}});print(json.dumps(result),flush=True);return result

def main(out):
 plan=json.loads(PLAN.read_text());assert file_hash(Path(__file__))==plan["evaluator_sha256"]
 checkpoint=ROOT/plan["candidate"];assert file_hash(checkpoint)==plan["candidate_sha256"]
 saved=torch.load(checkpoint,map_location="cpu");model=DaggerNet(saved["inputs"]);model.load_state_dict(saved["model"]);model.eval()
 out.mkdir(parents=True,exist_ok=False);shutil.copy2(PLAN,out/"plan.json");results=[]
 for spec in plan["specs"]:
  results.append(run_case(out,spec,plan,model,saved));write(out/"summary.json",{"cases":len(results),"successes":sum(r["success"] for r in results),"required_successes":plan["required_successes"],"results":results,"validation_loaded":False})
if __name__=="__main__":p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);main(p.parse_args().out)
