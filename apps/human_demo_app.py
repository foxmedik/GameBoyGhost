"""SDL demonstration recorder app; no second SDL framework is loaded."""
import ctypes, json, os, queue, shutil, socket, subprocess, sys, tarfile, threading
from datetime import datetime
from pathlib import Path
from PIL import Image
from pyboy import PyBoy
import sdl2
import sdl2.sdlttf as ttf

ROOT=Path(getattr(sys,"_MEIPASS",os.environ.get("GAMEBOY_AGENT_ROOT",Path(__file__).resolve().parents[1]))); ASSETS=ROOT/"assets"
if hasattr(sys, "_MEIPASS"):
 ROM=ASSETS/"ladx.gbc"; STATE=ASSETS/"house.state"
else:
 ROM=ROOT/"Legend of Zelda, The - Link's Awakening DX (USA, Europe) (Rev A) (SGB Enhanced).gbc"; STATE=ROOT/"runs/navigation-chain-house-v1/initial.state"
DEST="studio@192.168.50.27:/Users/studio/Developer/GameBoyAgent/runs/human-demos/incoming/"
BUTTONS=("up","down","left","right","a","b","start","select")
TASK_FILE=ROOT/"configs/human_demo_tasks.json"
def data_dir():
 p=Path.home()/"Library/Application Support/GameBoyGhost Demo Recorder"/"runs";p.mkdir(parents=True,exist_ok=True);return p
def local_ip():
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
 try:
  s.connect(("192.168.50.27",9));return s.getsockname()[0]
 finally:s.close()

class App:
 def __init__(self):
  self.tasks=json.loads(TASK_FILE.read_text())["tasks"];self.selected=0;self.boy=None;self.recording=False;self.ready=False;self.frame=0;self.session=None;self.actions=self.segments=self.tags=None;self.held=frozenset();self.seg=0;self.controllers=[];self.msg="Loading task preview…";self.q=queue.Queue();self.room=(0,0,0);self.world_room=0;self.xy=(0,0);self.on_studio=local_ip()=="192.168.50.27";self.previous_markers=set();self.countdown=0
  sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO|sdl2.SDL_INIT_GAMECONTROLLER);ttf.TTF_Init();self.win=sdl2.SDL_CreateWindow(b"GameBoyGhost Demo Recorder",0x1FFF0000,0x1FFF0000,1000,640,0);self.r=sdl2.SDL_CreateRenderer(self.win,-1,sdl2.SDL_RENDERER_ACCELERATED);self.tex=sdl2.SDL_CreateTexture(self.r,sdl2.SDL_PIXELFORMAT_RGB24,sdl2.SDL_TEXTUREACCESS_STREAMING,160,144);self.font=ttf.TTF_OpenFont(b"/System/Library/Fonts/Supplemental/Arial.ttf",18)
  for i in range(sdl2.SDL_NumJoysticks()):
   if sdl2.SDL_IsGameController(i):self.controllers.append(sdl2.SDL_GameControllerOpen(i))
  self.load_preview()
  if self.controllers:self.msg=("STUDIO PREVIEW — click START RUN" if self.on_studio else "MINI CAPTURE — click START RUN")
  else:self.msg="Pair controller, then restart app"
 def rect(self,x,y,w,h,c):sdl2.SDL_SetRenderDrawColor(self.r,*c);sdl2.SDL_RenderFillRect(self.r,sdl2.SDL_Rect(x,y,w,h))
 def text(self,x,y,v):
  if not v:return
  z=ttf.TTF_RenderUTF8_Blended(self.font,v.encode(),sdl2.SDL_Color(230,235,245,255));q=sdl2.SDL_CreateTextureFromSurface(self.r,z);sdl2.SDL_RenderCopy(self.r,q,None,sdl2.SDL_Rect(x,y,z.contents.w,z.contents.h));sdl2.SDL_DestroyTexture(q);sdl2.SDL_FreeSurface(z)
 def start(self):
  if self.recording:return
  task=self.tasks[self.selected];self.session=data_dir()/f"{task['id']}-{datetime.now().strftime('%Y%m%d-%H%M%S')}";(self.session/"frames").mkdir(parents=True);self.actions=(self.session/"actions.jsonl").open("x");self.segments=(self.session/"input_segments.jsonl").open("x");self.tags=(self.session/"tags.jsonl").open("x");self.boy.stop();self.load_preview()
  self.recording=True;self.ready=False;self.frame=0;self.held=frozenset();self.seg=0;self.previous_markers=set();self.msg=f"Recording {task['title']}"
 def state_path(self):return ROOT/self.tasks[self.selected]["state"]
 def load_preview(self):
  self.boy=PyBoy(str(ROM),window="null");self.boy.set_emulation_speed(0)
  with self.state_path().open("rb") as f:self.boy.load_state(f)
  self.boy.tick(1,render=True);m=self.boy.memory;self.room=tuple(int(m[a]) for a in (0xDBA5,0xFFF7,0xFFF6));self.world_room=int(m[0xFFF6] if self.room[0]==0 else m[0xDB9C]);self.xy=(int(m[0xFF98]),int(m[0xFF99]))
 def inputs(self):
  out=set();marks=set();p=((sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP,"up"),(sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN,"down"),(sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT,"left"),(sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT,"right"),(sdl2.SDL_CONTROLLER_BUTTON_B,"a"),(sdl2.SDL_CONTROLLER_BUTTON_A,"b"),(sdl2.SDL_CONTROLLER_BUTTON_BACK,"select"),(sdl2.SDL_CONTROLLER_BUTTON_START,"start"))
  for c in self.controllers:
   if sdl2.SDL_GameControllerGetAttached(c):
    for k,n in p:
     if sdl2.SDL_GameControllerGetButton(c,k):out.add(n)
    if sdl2.SDL_GameControllerGetButton(c,sdl2.SDL_CONTROLLER_BUTTON_X):marks.add("x_success")
    if sdl2.SDL_GameControllerGetButton(c,sdl2.SDL_CONTROLLER_BUTTON_Y):marks.add("y_contrast")
  return frozenset(out),marks
 def close_seg(self):
  if self.segments and self.frame>self.seg:self.segments.write(json.dumps({"start_frame":self.seg,"end_frame":self.frame,"length_frames":self.frame-self.seg,"buttons":sorted(self.held)})+"\n")
 def tick(self):
  if not self.recording:return
  held,markers=self.inputs()
  for marker in markers-self.previous_markers:self.tags.write(json.dumps({"frame":self.frame,"tag":marker,"task_id":self.tasks[self.selected]["id"]})+"\n")
  self.previous_markers=markers
  if held!=self.held:self.close_seg();self.held=held;self.seg=self.frame
  for b in BUTTONS:(self.boy.button_press if b in held else self.boy.button_release)(b)
  self.boy.tick(1,render=True);m=self.boy.memory;self.room=tuple(int(m[a]) for a in (0xDBA5,0xFFF7,0xFFF6));self.world_room=int(m[0xFFF6] if self.room[0]==0 else m[0xDB9C]);self.xy=(int(m[0xFF98]),int(m[0xFF99]));state={"room":self.room,"world_room":self.world_room,"x":self.xy[0],"y":self.xy[1],"health":int(m[0xDB5A]),"toadstool":int(m[0xDB4B])};self.actions.write(json.dumps({"frame":self.frame,"buttons":sorted(held),"state":state})+"\n");Image.fromarray(self.boy.screen.ndarray[:,:,:3]).save(self.session/"frames"/f"{self.frame:08d}.png");self.frame+=1
  if self.frame>=self.tasks[self.selected]["duration_seconds"]*60:self.end()
 def end(self):
  if not self.recording:return
  task=self.tasks[self.selected];self.recording=False;self.close_seg();self.actions.close();self.segments.close();self.tags.close();self.boy.stop();(self.session/"manifest.json").write_text(json.dumps({"format":"human-demo-v3","task_id":task["id"],"frames":self.frame},indent=2));self.countdown=300;self.msg="Saved — next run in 5";threading.Thread(target=self.send,daemon=True).start()
 def send(self):
  try:
   arc=self.session.with_suffix(".tar.gz");
   with tarfile.open(arc,"w:gz") as t:t.add(self.session,arcname=self.session.name)
   if self.on_studio:
    incoming=ROOT/"runs/human-demos/incoming";incoming.mkdir(parents=True,exist_ok=True);shutil.copy2(arc,incoming/arc.name);self.q.put("Saved directly to Studio incoming folder");return
   subprocess.run(["rsync","-az","--partial",str(arc),DEST],check=True);self.q.put("Sent to Studio")
  except Exception as e:self.q.put(f"Saved locally; delivery failed: {e}")
 def draw(self):
  self.rect(0,0,1000,640,(20,22,29,255))
  if self.boy:sdl2.SDL_UpdateTexture(self.tex,None,self.boy.screen.ndarray[:,:,:3].tobytes(),480);sdl2.SDL_RenderCopy(self.r,self.tex,None,sdl2.SDL_Rect(18,40,640,576))
  room=self.world_room
  for y in range(16):
   for x in range(16):self.rect(700+x*16,50+y*16,14,14,(244,186,66,255) if (x,y)==(room&15,room>>4) else (55,59,73,255))
  interior=" INTERIOR" if self.room[0] else ""
  task=self.tasks[self.selected];self.text(700,315,f"WORLD PANEL {room&15},{room>>4}{interior}");self.text(700,338,f"TASK {self.selected+1}/{len(self.tasks)}: {task['title']}");self.text(700,361,task['goal'][:30]);self.text(700,384,"X: "+task['x'][:27]);self.text(700,407,"Y: "+task['y'][:27]);self.text(700,430,f"{task['duration_seconds']} SEC  SAVED {self.task_count(task['id'])}/{task['target_runs']}");self.rect(700,455,125,45,(55,59,73,255));self.text(742,468,"PREV");self.rect(835,455,125,45,(55,59,73,255));self.text(878,468,"NEXT");self.rect(700,510,260,48,(47,130,103,255));self.text(780,523,"START RUN");self.rect(700,568,125,42,(150,93,42,255));self.text(720,580,"DISCARD");self.rect(835,568,125,42,(55,59,73,255));self.text(862,580,"END RUN");self.text(700,620,self.msg[:38]);sdl2.SDL_RenderPresent(self.r)
 def task_count(self,task_id):
  return sum(1 for p in data_dir().glob(f"{task_id}-*/manifest.json"))
 def discard(self):
  if not self.recording:return
  self.recording=False;self.close_seg();self.actions.close();self.segments.close();self.tags.close();self.boy.stop();shutil.rmtree(self.session,ignore_errors=True);self.load_preview();self.countdown=300;self.msg="Discarded — retry in 5"
 def choose(self,delta):
  if self.recording:return
  self.selected=(self.selected+delta)%len(self.tasks);self.boy.stop();self.load_preview();self.msg="Task selected — click START RUN"
 def loop(self):
  e=sdl2.SDL_Event();live=True
  while live:
   while sdl2.SDL_PollEvent(ctypes.byref(e)):
    if e.type==sdl2.SDL_QUIT:live=False
    elif e.type==sdl2.SDL_CONTROLLERDEVICEADDED:self.controllers.append(sdl2.SDL_GameControllerOpen(e.cdevice.which))
    elif e.type==sdl2.SDL_MOUSEBUTTONUP:
     x,y=e.button.x,e.button.y
     if 700<=x<=825 and 455<=y<=500:self.choose(-1)
     if 835<=x<=960 and 455<=y<=500:self.choose(1)
     if 700<=x<=960 and 510<=y<=558:self.start()
     if 700<=x<=825 and 568<=y<=610:self.discard()
     if 835<=x<=960 and 568<=y<=610:self.end()
   if self.recording:self.tick()
   elif self.countdown:
    self.countdown-=1;self.msg=f"Next run in {(self.countdown+59)//60}"
    if not self.countdown:self.start()
   try:self.msg=self.q.get_nowait()
   except queue.Empty:pass
   self.draw();sdl2.SDL_Delay(16)
  if self.boy:self.boy.stop()
if __name__=="__main__":App().loop()
