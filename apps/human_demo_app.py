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
  self.tasks=json.loads(TASK_FILE.read_text())["tasks"];self.selected=0;self.boy=None;self.recording=False;self.ready=False;self.frame=0;self.session=None;self.actions=self.segments=self.tags=None;self.held=frozenset();self.seg=0;self.controllers=[];self.msg="Loading task preview…";self.q=queue.Queue();self.room=(0,0,0);self.world_room=0;self.xy=(0,0);self.on_studio=local_ip()=="192.168.50.27";self.previous_markers=set();self.countdown=0;self.controls_y=390
  sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO|sdl2.SDL_INIT_GAMECONTROLLER);ttf.TTF_Init();self.win=sdl2.SDL_CreateWindow(b"GameBoyGhost Demo Recorder",0x1FFF0000,0x1FFF0000,1280,680,0);self.r=sdl2.SDL_CreateRenderer(self.win,-1,sdl2.SDL_RENDERER_ACCELERATED);self.tex=sdl2.SDL_CreateTexture(self.r,sdl2.SDL_PIXELFORMAT_RGB24,sdl2.SDL_TEXTUREACCESS_STREAMING,160,144);self.font=ttf.TTF_OpenFont(b"/System/Library/Fonts/Supplemental/Arial.ttf",18)
  self.rescan_controllers()
  self.load_preview()
  self.msg=self.capture_message()
 def rect(self,x,y,w,h,c):sdl2.SDL_SetRenderDrawColor(self.r,*c);sdl2.SDL_RenderFillRect(self.r,sdl2.SDL_Rect(x,y,w,h))
 def text(self,x,y,v):
  if not v:return
  z=ttf.TTF_RenderUTF8_Blended(self.font,v.encode(),sdl2.SDL_Color(230,235,245,255));q=sdl2.SDL_CreateTextureFromSurface(self.r,z);sdl2.SDL_RenderCopy(self.r,q,None,sdl2.SDL_Rect(x,y,z.contents.w,z.contents.h));sdl2.SDL_DestroyTexture(q);sdl2.SDL_FreeSurface(z)
 def controller_status(self):return sum(bool(sdl2.SDL_GameControllerGetAttached(c)) for c in self.controllers)
 def rescan_controllers(self):
  self.controllers=[]
  for i in range(sdl2.SDL_NumJoysticks()):
   if sdl2.SDL_IsGameController(i):
    c=sdl2.SDL_GameControllerOpen(i)
    if c:self.controllers.append(c)
 def capture_message(self):return ("STUDIO PREVIEW — click START RUN" if self.on_studio else "MINI CAPTURE — click START RUN") if self.controller_status() else "No controller found — pair one, then click RESCAN"
 def bluetooth_settings(self):
  subprocess.Popen(["open","x-apple.systempreferences:com.apple.BluetoothSettings-Settings.extension"]);self.msg="Bluetooth Settings opened — pair the SN30 Pro, then RESCAN"
 def wrap(self,v,n=34):
  words=v.split();lines=[];line=""
  for word in words:
   next_line=(line+" "+word).strip()
   if line and len(next_line)>n:lines.append(line);line=word
   else:line=next_line
  if line:lines.append(line)
  return lines
 def lines(self,x,y,v,n=34):
  for line in self.wrap(v,n):self.text(x,y,line);y+=21
  return y
 def start(self):
  if self.recording:return
  if not self.controller_status():self.msg="No controller detected. Pair it, then click RESCAN.";return
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
    if sdl2.SDL_GameControllerGetButton(c,sdl2.SDL_CONTROLLER_BUTTON_X):marks.add("x_discard")
    if sdl2.SDL_GameControllerGetAxis(c,sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT)>16000:marks.add("l2_good")
    if sdl2.SDL_GameControllerGetAxis(c,sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT)>16000:marks.add("r2_bad")
  return frozenset(out),marks
 def close_seg(self):
  if self.segments and self.frame>self.seg:self.segments.write(json.dumps({"start_frame":self.seg,"end_frame":self.frame,"length_frames":self.frame-self.seg,"buttons":sorted(self.held)})+"\n")
 def tick(self):
  if not self.recording:return
  held,markers=self.inputs()
  new_markers=markers-self.previous_markers
  if "x_discard" in new_markers:self.discard();return
  for marker in new_markers:self.tags.write(json.dumps({"frame":self.frame,"tag":marker,"task_id":self.tasks[self.selected]["id"]})+"\n")
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
  self.rect(0,0,1280,680,(20,22,29,255));self.text(18,20,"GAME PREVIEW")
  if self.boy:sdl2.SDL_UpdateTexture(self.tex,None,self.boy.screen.ndarray[:,:,:3].tobytes(),480);sdl2.SDL_RenderCopy(self.r,self.tex,None,sdl2.SDL_Rect(18,54,640,576))
  room=self.world_room
  for y in range(16):
   for x in range(16):self.rect(1010+x*16,50+y*16,14,14,(244,186,66,255) if (x,y)==(room&15,room>>4) else (55,59,73,255))
  interior=" INTERIOR" if self.room[0] else ""
  task=self.tasks[self.selected];self.text(680,20,f"TASK {self.selected+1}/{len(self.tasks)}");self.text(680,44,task['title']);y=self.lines(680,72,"OBJECTIVE  "+task['goal'],32);y=self.lines(680,y+10,"GOOD · L2  "+task['x'],32);y=self.lines(680,y+10,"BAD · R2  "+task['y'],32);self.text(680,y+8,f"{task['duration_seconds']} SEC  SAVED {self.task_count(task['id'])}/{task['target_runs']}");self.controls_y=max(390,y+38);self.rect(680,self.controls_y,140,44,(55,59,73,255));self.text(725,self.controls_y+12,"PREV");self.rect(830,self.controls_y,140,44,(55,59,73,255));self.text(875,self.controls_y+12,"NEXT");self.rect(680,self.controls_y+55,290,48,(47,130,103,255));self.text(775,self.controls_y+68,"START RUN");self.rect(680,self.controls_y+115,140,44,(150,93,42,255));self.text(700,self.controls_y+127,"X: DISCARD");self.rect(830,self.controls_y+115,140,44,(55,59,73,255));self.text(855,self.controls_y+127,"END RUN");self.text(680,self.controls_y+180,self.msg[:47]);self.text(1010,20,"OVERWORLD PANEL");self.text(1010,315,f"WORLD PANEL {room&15},{room>>4}{interior}");self.text(1010,355,f"CONTROLLER: {self.controller_status()} CONNECTED" if self.controller_status() else "CONTROLLER: NOT CONNECTED");self.rect(1010,385,256,44,(55,59,73,255));self.text(1050,397,"RESCAN CONTROLLERS");self.rect(1010,440,256,44,(62,85,129,255));self.text(1050,452,"BLUETOOTH SETTINGS");self.lines(1010,500,"L2 marks good. R2 marks bad. X discards the active run.",29);sdl2.SDL_RenderPresent(self.r)
 def task_count(self,task_id):
  return sum(1 for p in data_dir().glob(f"{task_id}-*/manifest.json"))
 def discard(self):
  if not self.recording:return
  self.recording=False;self.close_seg();self.actions.close();self.segments.close();self.tags.close();self.boy.stop();shutil.rmtree(self.session,ignore_errors=True);self.load_preview();self.countdown=300;self.msg="Discarded — retry in 5"
 def choose(self,delta):
  if self.recording:return
  self.selected=(self.selected+delta)%len(self.tasks);self.boy.stop();self.load_preview();self.msg=self.capture_message()
 def loop(self):
  e=sdl2.SDL_Event();live=True
  while live:
   while sdl2.SDL_PollEvent(ctypes.byref(e)):
    if e.type==sdl2.SDL_QUIT:live=False
    elif e.type==sdl2.SDL_CONTROLLERDEVICEADDED:self.rescan_controllers();self.msg=self.capture_message()
    elif e.type==sdl2.SDL_MOUSEBUTTONUP:
     x,y=e.button.x,e.button.y
     if 680<=x<=820 and self.controls_y<=y<=self.controls_y+44:self.choose(-1)
     if 830<=x<=970 and self.controls_y<=y<=self.controls_y+44:self.choose(1)
     if 680<=x<=970 and self.controls_y+55<=y<=self.controls_y+103:self.start()
     if 680<=x<=820 and self.controls_y+115<=y<=self.controls_y+159:self.discard()
     if 830<=x<=970 and self.controls_y+115<=y<=self.controls_y+159:self.end()
     if 1010<=x<=1266 and 385<=y<=429:self.rescan_controllers();self.msg=self.capture_message()
     if 1010<=x<=1266 and 440<=y<=484:self.bluetooth_settings()
   if self.recording:self.tick()
   elif self.countdown:
    self.countdown-=1;self.msg=f"Next run in {(self.countdown+59)//60}"
    if not self.countdown:self.start()
   try:self.msg=self.q.get_nowait()
   except queue.Empty:pass
   self.draw();sdl2.SDL_Delay(16)
  if self.boy:self.boy.stop()
if __name__=="__main__":App().loop()
