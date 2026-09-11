"""Render a verified learned specialist loop at native frame speed to MP4."""
import json,sys,subprocess,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
import gameboy_agent.training_env as training
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.navigation import reached
from gameboy_agent.dataset import sha256
from control_context import ControlContext
from run_skill_chain import senses

def main():
 out=ROOT/'runs/videos/learned-cliff-loop-v2';out.mkdir(parents=True,exist_ok=False)
 run=ROOT/'runs/navigation-cliff-specialists-v2/candidate/room_loop-house';manifest=run/'manifest.json';m=json.loads(manifest.read_text())
 for name,h in m['artifacts'].items():assert sha256(run/name)==h
 r=json.loads((run/'result.json').read_text());assert r['status']=='success' and r['navigation_damage']==0
 actions=r['actions'];goals=r['route']['goals'];cursor=0;frames=0;damage=0;milestones=[];recording=False
 video=out/'cliff-loop.mp4';fontpath=Path('/System/Library/Fonts/Supplemental/Arial.ttf')
 font=ImageFont.truetype(str(fontpath),22);small=ImageFont.truetype(str(fontpath),17)
 ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();log=(out/'encoding.log').open('w')
 process=subprocess.Popen([ffmpeg,'-y','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','640x688','-r','59.72750057','-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE,stderr=log)
 with tempfile.TemporaryDirectory() as tmp:
  rom=Path(tmp)/'game.gbc';shutil.copy2(run/'game.gbc',rom)
  base=training.TrainingEnv(rom,run/'initial.state',max_steps=2625,sword_curriculum=False);env=ControlContext(base)
  def emit(complete=False):
   nonlocal frames
   picture=Image.fromarray(base.pyboy.screen.ndarray[:,:,:3]).resize((640,576),Image.Resampling.NEAREST)
   canvas=Image.new('RGB',(640,688),'#111923');canvas.paste(picture,(0,80));draw=ImageDraw.Draw(canvas)
   draw.text((16,9),'GameBoyGhost — Cliff loop',font=font,fill='white')
   draw.text((16,42),'Learned navigator • House start • Development route',font=small,fill='#9ed9c7')
   labels=['Reach the lower path','Reach the cliff base','Detour through the western room','Return to the starting waypoint']
   text='Loop complete • No damage' if complete else f'Goal {cursor+1}/4: {labels[min(cursor,3)]}'
   draw.text((16,662),text,font=small,fill='white')
   process.stdin.write(canvas.tobytes());frames+=1
   if frames==1:canvas.save(out/'poster.png')
  original_advance=training.advance
  class FrameTap:
   def __init__(self,boy):self.boy=boy
   def __getattr__(self,name):return getattr(self.boy,name)
   def tick(self,*args,**kwargs):
    value=self.boy.tick(*args,**kwargs)
    if recording:emit()
    return value
  def captured_advance(boy,tracker,pressed,**kwargs):return original_advance(FrameTap(boy),tracker,pressed,**kwargs)
  training.advance=captured_advance
  try:
   env.reset(seed=0)
   for index,a in enumerate(actions):
    recording=index>=r['sword_step'];before=senses(base)
    env.step(np.asarray(a));after=senses(base)
    if recording:
     damage+=max(0,before.health-after.health)
     while cursor<len(goals) and reached(after.room,after.x,after.y,goals[cursor]):
      milestones.append(dict(goal=cursor+1,action=index+1,frame=frames,seconds=frames/59.72750057));cursor+=1
   assert cursor==4 and damage==0 and fingerprint(base)==r['fingerprint']
   gameplay_frames=frames
   for _ in range(120):emit(complete=True)
   result=dict(video=str(video),source_manifest=str(manifest),source_manifest_sha256=sha256(manifest),teacher_demonstration=False,learned_policy_rollout=True,continuous_episode=True,
    starts_after_sword=True,actions=len(actions)-r['sword_step'],milestones=milestones,gameplay_frames=gameplay_frames,presentation_hold_frames=120,
    fps=59.72750057,duration_seconds=frames/59.72750057,navigation_damage=damage,final_fingerprint=fingerprint(base),replay_verified=True,audio=False)
  finally:
   training.advance=original_advance;env.close();process.stdin.close();code=process.wait();log.close()
  assert code==0
  result['video_sha256']=sha256(video);(out/'manifest.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':main()
