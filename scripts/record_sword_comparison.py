"""Shareable, exact-replay comparison of frozen teacher demonstrations."""
import json,sys,shutil,tempfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import pyarrow.parquet as pq
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg
import gameboy_agent.training_env as training
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.dataset import sha256,pack_observation
from control_context import ControlContext
from run_skill_chain import senses
EXP=ROOT/'runs/proximity-sword-48-v2'
OUT=ROOT/'runs/videos/selective-sword-v2-comparison'
FPS=59.72750057/2
W,H=1024,680
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
FONTS={s:ImageFont.truetype(FONT,s) for s in (18,22,24,28,36,48,64)}
BG='#101923';WHITE='#f2f5f8';MUTED='#a5b2c0';GREEN='#89dfb8';AMBER='#ffcc80'

def text(draw,xy,value,size=24,color=WHITE):draw.text(xy,value,font=FONTS[size],fill=color)

def replay(case,variant,batch):
    source=EXP/f"{case['segment_id']}-{variant}.json";r=json.loads(source.read_text())
    assert r['success'] and r['damage']==0 and r['replay_verified']
    tracepath=batch/case['source_path'];assert sha256(tracepath)==case['source_sha256']
    meta=json.loads((tracepath.parent/'manifest.json').read_text())
    trace=pq.read_table(tracepath,columns=['action','observation']).to_pydict()
    frames=[];swings=0;recording=False;damage=0
    original=training.advance
    with tempfile.TemporaryDirectory() as tmp:
        rom=Path(tmp)/'game.gbc';shutil.copy2(batch/'assets/game.gbc',rom)
        base=training.TrainingEnv(rom,batch/'assets'/f"{meta['start']}.state",max_steps=meta['max_steps'],sword_curriculum=False)
        env=ControlContext(base)
        def capture():return (Image.fromarray(base.pyboy.screen.ndarray[:,:,:3].copy()),swings)
        class Tap:
            def __init__(self,boy):self.boy=boy
            def __getattr__(self,name):return getattr(self.boy,name)
            def tick(self,*args,**kwargs):
                nonlocal swings
                before=int(self.boy.memory[0xC137]);v=self.boy.tick(*args,**kwargs)
                if recording:
                    after=int(self.boy.memory[0xC137]);swings+=int(before not in (1,2,3,4) and after in (1,2,3,4))
                    frames.append(capture())
                return v
        def tapped(boy,tracker,pressed,**kwargs):return original(Tap(boy),tracker,pressed,**kwargs)
        training.advance=tapped
        try:
            obs,_=env.reset(seed=meta['seed'])
            for a in trace['action'][:case['step']]:obs,*_=env.step(np.asarray(a))
            assert pack_observation(obs,meta['observation_layout'])==trace['observation'][case['step']]
            base.config['max_steps']=base.total_steps+129
            assert fingerprint(base)==r['start_fingerprint'];initial=capture();recording=True
            for a in r['actions']:
                before=senses(base);env.step(np.asarray(a));damage+=max(0,before.health-senses(base).health)
            assert fingerprint(base)==r['final_fingerprint'] and damage==0
            assert swings==r['actual_swing_starts'] and len(frames)==r['frames']
        finally:training.advance=original;env.close()
    return initial,frames,dict(source=str(source),sha256=sha256(source),final_fingerprint=r['final_fingerprint'],replay_verified=True,game_frames=len(frames),swings=swings,damage=damage)

def board(title,left,right,done=(False,False),note=''):
    canvas=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(canvas)
    text(d,(28,18),'GameBoyGhost',28,GREEN);text(d,(28,55),title,36)
    for x,label,sample,finished,color in [(24,'BEFORE  /  Cadence teacher',left,done[0],AMBER),(520,'AFTER  /  Terrain + motion',right,done[1],GREEN)]:
        text(d,(x,109),label,22,color)
        canvas.paste(sample[0].resize((480,432),Image.Resampling.NEAREST),(x,146))
        text(d,(x,590),f'Swings: {sample[1]}',28,color)
        if finished:text(d,(x+245,596),'Goal reached',22,GREEN)
    text(d,(24,636),note or 'Verified teacher replays  |  Normal game speed  |  Silent',18,MUTED)
    return canvas

def card(title,lines):
    c=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(c)
    text(d,(48,48),'GameBoyGhost',28,GREEN);text(d,(48,170),title,48)
    for i,(line,color) in enumerate(lines):text(d,(48,270+i*58),line,28,color)
    text(d,(48,625),'Scripted teacher experiment — not a trained-policy result',22,MUTED)
    return c

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    plan=json.loads((EXP/'plan.json').read_text());report=json.loads((EXP/'result.json').read_text())
    assert report['gate_passed']['terrain_motion']
    batch=Path(json.loads((ROOT/'runs/navigation-cache-v2/manifest.json').read_text())['source_batch'])
    cases=[('c975b2fd3b62','1 / Clear ground','Skip swings when the path is clear.'),('763b4286fbad','2 / Cuttable bushes','Keep the swing that opens the path.'),('ad819075151c','3 / Entering another room','Preserve sword use before an unseen room entry.')]
    video=OUT/'gameboyghost-selective-sword.mp4';ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    log=(OUT/'encoding.log').open('w')
    process=subprocess.Popen([ffmpeg,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE,stderr=log)
    count=0;segments=[]
    def emit(c):
        nonlocal count
        process.stdin.write(c.tobytes());count+=1
    def hold(c,seconds):
        for _ in range(round(seconds*FPS)):emit(c)
    try:
        hold(card('Teaching Link when to swing', [('Before / after on identical starting states',WHITE),('Clear paths. Cut bushes. Guard room entries.',GREEN)]),2.5)
        for prefix,title,note in cases:
            case=next(c for c in plan['cases'] if c['segment_id'].startswith(prefix))
            li,lf,lm=replay(case,'cadence',batch);ri,rf,rm=replay(case,'terrain_motion',batch)
            start=count
            hold(board(title,li,ri,note=note),1.2)
            for i in range(0,max(len(lf),len(rf)),2):
                c=board(title,lf[min(i,len(lf)-1)],rf[min(i,len(rf)-1)],(i>=len(lf),i>=len(rf)),note)
                emit(c)
            last=board(title,lf[-1],rf[-1],(True,True),note)
            hold(last,1.8)
            if prefix=='763b4286fbad':last.save(OUT/'poster.png')
            segments.append(dict(case_id=case['segment_id'],title=title,start_seconds=start/FPS,end_seconds=count/FPS,before=lm,after=rm))
            print('Verified and recorded',title,flush=True)
        hold(card('66.5% fewer sword swings', [('747 → 250 swings across 48 known cases',GREEN),('41 → 42 goals reached  |  No lost successes',WHITE),('No increased per-case damage  |  No deaths',WHITE),('144 rollouts independently replay-verified',MUTED)]),4)
    finally:process.stdin.close();code=process.wait();log.close()
    assert code==0
    subprocess.run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],check=True)
    manifest=dict(video=str(video),video_sha256=sha256(video),bytes=video.stat().st_size,frames=count,fps=FPS,duration_seconds=count/FPS,
        resolution=[W,H],audio=False,teacher_demonstration=True,learned_policy_rollout=False,continuous_episode=False,
        presentation='Three separate paired cases; native game speed, completed panels freeze while the other finishes; title/end holds.',
        source_report_sha256=sha256(EXP/'result.json'),segments=segments,replay_verified=True,full_decode_verified=True)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest),flush=True)
if __name__=='__main__':main()
