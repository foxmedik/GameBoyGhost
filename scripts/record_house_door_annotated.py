"""Record a complete verified physical replay with chapter annotations and narration."""
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import textwrap

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.battle_ready_endpoint import require_battle_ready
from run_toadstool_progression import apply

CHAPTERS = [
    (0, 'The teacher is qualified', '20 / 20 house cases\n4 / 4 actual half-heart recoveries\n24 / 24 exact replays',
     'This is the complete guided route from the supplied house to the opened Nightmare boss door. The teacher has now passed all twenty house cases and all four actual half-heart recovery challenges. Every case replayed exactly. This new recording shows the whole physical route, at normal speed, without intermediate state loads.'),
    (4928, 'A continuous route', 'Sword acquired\nPhysical controls throughout\nGuided, not a learned end-to-end policy',
     'The sword is acquired. The important distinction is that this is a qualified guided teacher, using existing learned specialists and explicit route controllers. It is not a newly trained end-to-end policy. No learner labels or training were generated during this work.'),
    (9000, 'Reproducible failures', 'A failed case stayed failed\nEvery command was preserved\nEvery failure was independently replayed',
     'The route proof came before reliability. We preserved failed attempts and replayed them from the original house. That let us separate reproducible control errors from unexplained variation. A candidate that missed even one frozen qualification case was rejected.'),
    (13422, 'React to the bats', 'Observe nearby Keese\nWait for sword animation to finish\nCheck actual facing before a new strike',
     'The mushroom cave exposed a timing weakness. A fixed climb could let a bat reach Link before the controller reacted. The corrected climb and crossing check nearby bats one frame at a time, wait for sword animation, and verify actual facing before striking.'),
    (15800, 'Recover the doorway', 'Bat contact can shift the exit pose\nRecheck horizontal alignment\nSettle pickup dialogue before crossing',
     'Returning through this cave revealed another failure. Bat contact could knock Link sideways, while a crossing routine kept pressing down into the doorway edge. We added observed defense and checked alignment during the crossing. Pickups also need their dialogue settled before movement resumes.'),
    (21862, 'Keep the whole route honest', 'Witch exchange complete\nTarin and Tail Key next\nLater control changes were tested from the house',
     'The witch exchange is complete. Changes deep in the dungeon can change the timing of later encounters, so a successful local fix was never enough. Development regressions started from this same house state and had to reach the final door, then replay every command.'),
    (27946, 'A frozen qualification gate', 'Original cases unchanged\nOriginal whole-route limits unchanged\nSame final health and equipment contract',
     'The Tail Key is now obtained. The qualification cases, whole-route limits, and endpoint requirements stayed frozen. We corrected control logic and used bounded local encounter allowances, but never changed what counted as a pass.'),
    (31718, 'Target the live threat', 'Hardhat beetles require careful facing\nIgnore enemies already falling\nKeep the shield raised',
     'Inside Tail Cave, a hardhat controller could swing at an enemy already falling while a live beetle approached from another direction. The correction targets active enemies, holds the shield, and observes the real facing after sword lock ends.'),
    (33000, 'A turn is not a guarantee', 'Projectile guard checks actual facing\nSword animation can block a turn\nHidden enemies need time to emerge',
     'The Compass room exposed a cached-facing bug. The controller remembered an upward turn even though sword animation had prevented it. It now checks the actual facing each time it guards a projectile. We also allowed enough bounded time for repeated enemy emergence and guarding.'),
    (35500, 'Align before the next leg', 'Use crossed thresholds, not exact pixels\nRejoin the safe lane after combat\nA pursuit endpoint is not an exit stance',
     'One approach required exactly one pixel coordinate. Link could step past it and continue into a wall. Directional thresholds fixed that. Bat pursuit also ended away from a safe exit lane, so the teacher now rejoins the solid lane before moving north.'),
    (38300, 'Clear Gels before the Spark', 'Handle cling and release\nMatch approach and attack reach\nRealign the top lane before crossing',
     'Gels could delay the Spark crossing, cling to Link, or stop between mismatched approach and attack distances. We matched those distances, allowed a full cling-and-release cycle, and realigned the top lane before waiting for the Spark.'),
    (39368, 'Stay on connected floor', 'Shield recoil changes position\nUse safe approach lanes\nFinish flipped beetles within reach',
     'The spiked beetles needed safe connected approach lanes. Chasing a target diagonally could lead toward a pit. Another flipped beetle rested at the bottom edge, beyond the chosen stance. The corrected controller uses the available central floor to finish it without leaving the safe region.'),
    (40534, 'Feather and real recovery', 'Feather obtained physically\nRecovery challenges reached actual health 4\nEvery recovery ended at full health',
     'Roc’s Feather is obtained through normal play. The four recovery challenges were real: Link reached the required pre-Feather arrival at four health units through physical enemy contact. Each then completed the uninterrupted route and finished at full health. No health value was written into the game.'),
    (42500, 'Recoil needs continuous checks', 'Worm guards stay on solid floor\nCorrect waypoint overshoot\nMaintain the clear aisle throughout the move',
     'The worm encounters exposed pit geometry and recoil problems. A side guard could cross a pit, or recoil could push Link out of an aisle after a waypoint was considered complete. The teacher now uses safe guard positions and maintains alignment throughout the movement, with bounded waits for patrol cycles.'),
    (44368, 'The final physical sequence', 'Third key collected\nNightmare Key next\nJump landing and combat remain observed',
     'The final sequence includes the Nightmare Key, a pit crossing, and the miniboss. Earlier candidates failed on jump landings and nearby enemy contact. The route now checks the landing and handles threats around the crossing before proceeding.'),
    (47000, 'Rolling Bones and the door', 'Miniboss handled by the guided controller\nOpen the Nightmare door\nStop outside the boss room',
     'Rolling Bones is the last combat obstacle in this route. After the clear, the teacher continues through the final traps and opens the Nightmare door. The target ends outside the boss room. The boss fight is outside this milestone.'),
    (48737, 'Checkpoint verified', '20 / 20 house + 4 / 4 recovery\nFull health • Sword A • Feather B\nClean restore and independent backup verified',
     'The door is open, and Link remains outside, grounded and settled, at full health, with sword on A and Roc’s Feather on B. All twenty-four qualification cases passed. A fresh environment also passed the tests, reproduced the exact replay, and ran the teacher successfully. The source and artifacts are independently backed up.'),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    pin = json.loads((ROOT / 'reports/house-to-boss-door-v1/final-release-pin.json').read_text())
    if not pin['original_goals_complete']:
        raise RuntimeError('Recording is permitted only after the original goals are complete')
    out = ROOT / args.output
    out.mkdir(parents=True, exist_ok=False)
    chapters = [dict(frame=f, title=t, notes=n, narration=v) for f,t,n,v in CHAPTERS]
    if any('wipe' in str(c).lower() for c in chapters):
        raise RuntimeError('Excluded narration topic')
    (out / 'chapters.json').write_text(json.dumps(chapters, indent=2)+'\n')
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    audio = []
    for index,c in enumerate(chapters):
        text_path = out / f'narration-{index:02}.txt'
        text_path.write_text(c['narration']+'\n')
        path = out / f'narration-{index:02}.aiff'
        subprocess.run(['/usr/bin/say','-v','Samantha','-r','168','-f',str(text_path),'-o',str(path)],check=True)
        audio.append(path)
    run = ROOT / 'runs/house-door-teacher-qualification-v27/fresh-house-00'
    continuation = json.loads((run / 'continuation.json').read_text())
    for name,h in continuation['sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:
            raise RuntimeError('Input artifact hash mismatch: '+name)
    start = continuation['start']
    class RecordingEnv(ProgressionEnv):
        def post_state_load(self):
            super().post_state_load()
            for _ in range(intro*fps):emit(0)
            self.pyboy=RecordingBoy(self.pyboy)

    env = RecordingEnv(ROOT/start['rom'], ROOT/start['initial_state'], max_steps=30000,
                         max_frames=150000, completion_milestone=None)
    font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
    bold_path = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
    fonts = {s:ImageFont.truetype(font_path,s) for s in [18,20,23,26]}
    bold = {s:ImageFont.truetype(bold_path,s) for s in [20,22,30,34,38]}
    width,height,fps = 1280,720,30
    intro,outro,total = 8,24,48737
    chapter_frames = [c['frame'] for c in chapters]
    silent = out/'full-route-silent.mp4'
    encoding_log = (out/'encoding.log').open('w')
    encoder = subprocess.Popen([ffmpeg,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
        '-s','1280x720','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','veryfast',
        '-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(silent)],
        stdin=subprocess.PIPE,stderr=encoding_log)
    ticks=0;rendered=0;saved=set()

    def emit(frame):
        nonlocal rendered
        state=snapshot(env.pyboy)
        index=max(0,bisect.bisect_right(chapter_frames,frame)-1)
        c=chapters[index]
        canvas=Image.new('RGB',(width,height),(10,17,29));d=ImageDraw.Draw(canvas)
        d.text((30,18),'GAMEBOYGHOST',font=bold[30],fill=(237,244,252))
        d.text((362,25),'HOUSE → NIGHTMARE DOOR',font=fonts[20],fill=(127,157,183))
        d.rounded_rectangle((927,17,1250,55),radius=12,fill=(19,66,64))
        d.text((945,25),'GUIDED TEACHER QUALIFIED',font=bold[20],fill=(123,235,198))
        game=Image.fromarray(env.pyboy.screen.ndarray[:,:,:3]).resize((640,576),Image.Resampling.NEAREST)
        canvas.paste(game,(30,78))
        d.rounded_rectangle((704,78,1250,654),radius=16,fill=(18,29,45))
        d.text((732,101),f'CHAPTER {index+1:02} / {len(chapters):02}',font=fonts[18],fill=(110,212,222))
        y=143
        for line in textwrap.wrap(c['title'],width=25):
            d.text((732,y),line,font=bold[34],fill=(240,245,252));y+=43
        y+=28
        for note in c['notes'].splitlines():
            for j,line in enumerate(textwrap.wrap(note,width=37)):
                d.text((732,y),('• ' if j==0 else '  ')+line,font=fonts[23],fill=(185,205,225));y+=32
            y+=15
        d.line((732,486,1222,486),fill=(47,65,84),width=2)
        d.text((732,508),f'HEALTH  {state["health"]/8:g} / {state["max_hearts"]}',font=bold[22],fill=(125,234,185))
        names={0:'None',1:'Sword',4:'Shield',10:'Feather',12:'Powder'}
        inv=state['inventory']
        d.text((732,547),f'A  {names.get(inv[1],str(inv[1]))}     B  {names.get(inv[0],str(inv[0]))}',font=fonts[23],fill=(233,240,247))
        d.text((732,587),f'GAME TIME  {frame//3600:02}:{frame//60%60:02}   •   FRAME {frame:,}',font=fonts[18],fill=(134,157,181))
        d.text((30,681),'Complete physical route  •  Original house start  •  No intermediate state loads',font=fonts[18],fill=(151,175,196))
        d.rounded_rectangle((30,663,1250,668),radius=2,fill=(40,56,72))
        if frame:d.rounded_rectangle((30,663,30+int(1220*min(1,frame/total)),668),radius=2,fill=(89,211,199))
        encoder.stdin.write(canvas.tobytes());rendered+=1
        if index not in saved:
            canvas.save(out/f'chapter-{index:02}.png');saved.add(index)
        if frame==total and not (out/'final-frame.png').exists():canvas.save(out/'final-frame.png')

    class RecordingBoy:
        def __init__(self,boy):self.boy=boy
        def __getattr__(self,name):return getattr(self.boy,name)
        def tick(self,count=1,render=True):
            nonlocal ticks
            result=None
            for _ in range(count):
                result=self.boy.tick(1,render=True);ticks+=1
                if ticks%2==0:emit(ticks)
            return result

    commands=0
    try:
        env.reset(seed=0)
        for segment in continuation['replay_segments']:
            with (ROOT/segment).open() as stream:
                for line in stream:
                    row=json.loads(line);info=apply(env,row['command'])[4]
                    if (fingerprint(env)!=row['fingerprint'] or env.frames!=row['frame']
                        or json.loads(json.dumps(snapshot(env.pyboy)))!=row['after'] or info['events']!=row['events']):
                        raise RuntimeError(f'Recording replay mismatch at {commands}')
                    commands+=1
                    if commands%2000==0:print('Recorded and verified commands',commands,flush=True)
        if json.loads(json.dumps(env.journal.state()))!=json.loads((run/'journal.json').read_text()):raise RuntimeError('Journal mismatch')
        final=require_battle_ready(env)
        if not env.pyboy.memory[0xD90B]&4 or env.pyboy.memory[0xC188]:raise RuntimeError('Door not settled/open')
        if ticks!=env.frames or ticks!=total:raise RuntimeError(f'Capture frame count mismatch: captured={ticks}, environment={env.frames}, expected={total}')
        for _ in range(outro*fps):emit(total)
    finally:
        env.close();encoder.stdin.close();returncode=encoder.wait();encoding_log.close()
    if returncode:raise RuntimeError('Video encoder failed')
    duration=rendered/fps
    final_video=out/'house-to-nightmare-door-annotated.mp4'
    cmd=[ffmpeg,'-y','-loglevel','error','-i',str(silent)]
    filters=[]
    for index,path in enumerate(audio):
        cmd+=['-i',str(path)]
        delay=round(1000*(intro+chapters[index]['frame']/60))
        if index==0:delay=1000
        filters.append(f'[{index+1}:a]adelay={delay}|{delay}[a{index}]')
    filters.append(''.join(f'[a{i}]' for i in range(len(audio)))+f'amix=inputs={len(audio)}:duration=longest:normalize=0,apad[a]')
    cmd+=['-filter_complex',';'.join(filters),'-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','160k',
          '-t',str(duration),'-movflags','+faststart',str(final_video)]
    subprocess.run(cmd,check=True)
    report=dict(success=True,exact_replay=True,commands=commands,emulator_frames=ticks,
                rendered_frames=rendered,fps=fps,duration_seconds=duration,chapters=len(chapters),
                final=final,door_open=True,source_run=str(run.relative_to(ROOT)),
                original_goals_complete_before_recording=True,narration='macOS Samantha synthetic voice',
                full_route_without_cuts=True,video=str(final_video),sha256=hashlib.sha256(final_video.read_bytes()).hexdigest())
    (out/'recording-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
