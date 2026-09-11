"""SDL demonstration recorder app; no second SDL framework is loaded."""
import ctypes, json, queue, subprocess, sys, tarfile, threading
from datetime import datetime
from pathlib import Path
from PIL import Image
from pyboy import PyBoy
import sdl2
import sdl2.sdlttf as ttf

ROOT=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parents[1])); ASSETS=ROOT/"assets"
ROM=ASSETS/"ladx.gbc"; STATE=ASSETS/"house.state"; DEST="studio@192.168.50.27:/Users/studio/Developer/GameBoyAgent/runs/human-demos/incoming/"
BUTTONS=("up","down","left","right","a","b","start","select")
def data_dir():
 p=Path.home()/"Library/Application Support/GameBoyGhost Demo Recorder"/"runs";p.mkdir(parents=True,exist_ok=True);return p

class App:
 def __init__(self):
  self.boy=None;self.recording=False;self.ready=False;self.frame=0;self.session=None;self.actions=self.segments=None;self.held=frozenset();self.seg=0;self.controllers=[];self.msg="Click START RUN";self.q=queue.Queue();self.room=(0,0,0);self.xy=(0,0)
  sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO|sdl2.SDL_INIT_GAMECONTROLLER);ttf.TTF_Init();self.win=sdl2.SDL_CreateWindow(b"GameBoyGhost Demo Recorder",0x1FFF0000,0x1FFF0000,1000,640,0);self.r=sdl2.SDL_CreateRenderer(self.win,-1,sdl2.SDL_RENDERER_ACCELERATED);self.tex=sdl2.SDL_CreateTexture(self.r,sdl2.SDL_PIXELFORMAT_RGB24,sdl2.SDL_TEXTUREACCESS_STREAMING,160,144);self.font=ttf.TTF_OpenFont(b"/System/Library/Fonts/Supplemental/Arial.ttf",18)
  for i in range(sdl2.SDL_NumJoysticks()):
   if sdl2.SDL_IsGameController(i):self.controllers.append(sdl2.SDL_GameControllerOpen(i))
  if self.controllers:self.msg="Controller ready — click START RUN"
 def rect(self,x,y,w,h,c):sdl2.SDL_SetRenderDrawColor(self.r,*c);sdl2.SDL_RenderFillRect(self.r,sdl2.SDL_Rect(x,y,w,h))
 def text(self,x,y,v):
  if not v:return
  z=ttf.TTF_RenderUTF8_Blended(self.font,v.encode(),sdl2.SDL_Color(230,235,245,255));q=sdl2.SDL_CreateTextureFromSurface(self.r,z);sdl2.SDL_RenderCopy(self.r,q,None,sdl2.SDL_Rect(x,y,z.contents.w,z.contents.h));sdl2.SDL_DestroyTexture(q);sdl2.SDL_FreeSurface(z)
 def start(self):
  if self.recording:return
  self.session=data_dir()/datetime.now().strftime("%Y%m%d-%H%M%S");(self.session/"frames").mkdir(parents=True);self.actions=(self.session/"actions.jsonl").open("x");self.segments=(self.session/"input_segments.jsonl").open("x");self.boy=PyBoy(str(ROM),window="null");self.boy.set_emulation_speed(0)
  with STATE.open("rb") as f:self.boy.load_state(f)
  self.recording=True;self.ready=False;self.frame=0;self.held=frozenset();self.seg=0;self.msg="Recording — reach the Toadstool"
 def inputs(self):
  out=set();p=((sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP,"up"),(sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN,"down"),(sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT,"left"),(sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT,"right"),(sdl2.SDL_CONTROLLER_BUTTON_B,"a"),(sdl2.SDL_CONTROLLER_BUTTON_A,"b"),(sdl2.SDL_CONTROLLER_BUTTON_BACK,"select"),(sdl2.SDL_CONTROLLER_BUTTON_START,"start"))
  for c in self.controllers:
   if sdl2.SDL_GameControllerGetAttached(c):
    for k,n in p:
     if sdl2.SDL_GameControllerGetButton(c,k):out.add(n)
  return frozenset(out)
 def close_seg(self):
  if self.segments and self.frame>self.seg:self.segments.write(json.dumps({"start_frame":self.seg,"end_frame":self.frame,"length_frames":self.frame-self.seg,"buttons":sorted(self.held)})+"\n")
 def tick(self):
  if not self.recording:return
  held=self.inputs()
  if held!=self.held:self.close_seg();self.held=held;self.seg=self.frame
  for b in BUTTONS:(self.boy.button_press if b in held else self.boy.button_release)(b)
  self.boy.tick(1,render=True);m=self.boy.memory;self.room=tuple(int(m[a]) for a in (0xDBA5,0xFFF7,0xFFF6));self.xy=(int(m[0xFF98]),int(m[0xFF99]));state={"room":self.room,"x":self.xy[0],"y":self.xy[1],"health":int(m[0xDB5A]),"toadstool":int(m[0xDB4B])};self.actions.write(json.dumps({"frame":self.frame,"buttons":sorted(held),"state":state})+"\n");Image.fromarray(self.boy.screen.ndarray[:,:,:3]).save(self.session/"frames"/f"{self.frame:08d}.png");self.frame+=1
  if state["toadstool"]:self.ready=True;self.msg="Toadstool acquired — click END RUN"
 def end(self):
  if not self.ready:self.msg="END RUN unlocks after the Toadstool";return
  self.recording=False;self.close_seg();self.actions.close();self.segments.close();self.boy.stop();(self.session/"manifest.json").write_text(json.dumps({"format":"human-demo-v2","frames":self.frame,"toadstool":1},indent=2));self.msg="Packing and sending to Studio…";threading.Thread(target=self.send,daemon=True).start()
 def send(self):
  try:
   arc=self.session.with_suffix(".tar.gz");
   with tarfile.open(arc,"w:gz") as t:t.add(self.session,arcname=self.session.name)
   subprocess.run(["rsync","-az","--partial",str(arc),DEST],check=True);self.q.put("Sent to Studio")
  except Exception as e:self.q.put(f"Saved locally; delivery failed: {e}")
 def draw(self):
  self.rect(0,0,1000,640,(20,22,29,255))
  if self.boy:sdl2.SDL_UpdateTexture(self.tex,None,self.boy.screen.ndarray[:,:,:3].tobytes(),480);sdl2.SDL_RenderCopy(self.r,self.tex,None,sdl2.SDL_Rect(18,40,640,576))
  self.text(700,20,"16x16 ROOM GRID");room=self.room[2]
  for y in range(16):
   for x in range(16):self.rect(700+x*16,50+y*16,14,14,(244,186,66,255) if (x,y)==(room&15,room>>4) else (55,59,73,255))
  self.text(700,315,f"ROOM {room:02X}  LINK {self.xy[0]},{self.xy[1]}");self.text(700,340,f"CELL {self.xy[0]//16},{(self.xy[1]-4)//16}");self.rect(700,380,260,54,(47,130,103,255));self.text(780,397,"START RUN");self.rect(700,445,260,54,(150,93,42,255) if self.ready else (50,54,65,255));self.text(788,462,"END RUN");self.text(700,525,self.msg[:30]);self.text(700,548,self.msg[30:60]);sdl2.SDL_RenderPresent(self.r)
 def loop(self):
  e=sdl2.SDL_Event();live=True
  while live:
   while sdl2.SDL_PollEvent(ctypes.byref(e)):
    if e.type==sdl2.SDL_QUIT:live=False
    elif e.type==sdl2.SDL_CONTROLLERDEVICEADDED:self.controllers.append(sdl2.SDL_GameControllerOpen(e.cdevice.which))
    elif e.type==sdl2.SDL_MOUSEBUTTONUP:
     x,y=e.button.x,e.button.y
     if 700<=x<=960 and 380<=y<=434:self.start()
     if 700<=x<=960 and 445<=y<=499:self.end()
   self.tick()
   try:self.msg=self.q.get_nowait()
   except queue.Empty:pass
   self.draw();sdl2.SDL_Delay(16)
  if self.boy:self.boy.stop()
if __name__=="__main__":App().loop()
