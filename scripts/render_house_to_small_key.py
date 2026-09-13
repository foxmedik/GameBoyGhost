"""Render every frame of a verified house-to-key trace with evidence annotations."""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.progression import snapshot
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.world_memory import file_hash
from run_toadstool_progression import apply

SOURCE = ROOT / 'runs/state-driven-tail-cave-disengage-guarded-v1/development-house-00'
OUT = ROOT / 'runs/videos/house-to-small-key-annotated-v1'
FPS = 59.72750057 / 2


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    rows = [json.loads(line) for line in (SOURCE / 'trajectory.jsonl').read_text().splitlines()]
    journal = json.loads((SOURCE / 'journal.json').read_text())
    milestones = [(0, 'House start', 'Reach the beach and acquire the sword')]
    labels = {
        'sword_acquired': ('Sword acquired', 'Travel through the forest to the mushroom'),
        'toadstool_acquired': ('Mushroom acquired', 'Return through the cave to the witch'),
        'powder_available': ('Magic Powder acquired', 'Return to the forest and cure Tarin'),
        'raccoon_cured': ('Tarin cured', 'Reach and open the Tail Key chest'),
        'tail_key_acquired': ('Tail Key acquired', 'Travel to the Tail Cave entrance'),
        'tail_cave_opened': ('Tail Cave unlocked', 'Enter the dungeon and reach the beetles'),
        'tail_cave_entered': ('Tail Cave entered', 'Defeat the beetles and collect the Small Key'),
    }
    for name, index in journal['milestones'].items():
        if name in labels:
            milestones.append((journal['events'][index]['frame'], *labels[name]))
    milestones.append((rows[-1]['frame'], 'First Small Key acquired', 'Current reliable progression milestone reached'))
    milestones.sort()
    evidence = json.loads((SOURCE / 'evidence.json').read_text())
    notes = [(0, 'Continuous supplied-house start; shield already equipped.')]
    note_labels = {
        'live_forest_handoff': 'Forest handoff verified from live room and inventory state.',
        'verified_block_push': 'Cave block push verified by a changed room object.',
        'verified_return_push': 'Return-path block push verified from live terrain.',
        'downstream_teacher_recovery_started': 'Bounded learned movement hands control to guided recovery.',
        'tail_cave_title_dismissed': 'Dungeon title dialogue detected and dismissed.',
        'tail_cave_teacher_recovery_started': 'Cave teacher takes over before the first model proposal executes.',
        'tail_cave_first_key_collected': 'Small Key count increased to 1; Link is alive.',
    }
    for event in evidence:
        if event['kind'] in note_labels:
            notes.append((event['frame'], note_labels[event['kind']]))
    notes.sort()
    regular = '/System/Library/Fonts/Supplemental/Arial.ttf'
    bold = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
    fonts = {n: ImageFont.truetype(regular, n) for n in (16, 18, 20, 24)}
    title = ImageFont.truetype(bold, 28)
    video = OUT / 'house-to-small-key-annotated.mp4'
    log = (OUT / 'encoding.log').open('w')
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    encoder = subprocess.Popen([ffmpeg, '-y', '-loglevel', 'error', '-f', 'rawvideo',
        '-pix_fmt', 'rgb24', '-s', '1040x720', '-r', str(FPS), '-i', '-', '-an',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(video)], stdin=subprocess.PIPE, stderr=log)
    env = ProgressionEnv(SOURCE/'game.gbc', SOURCE/'initial.state', max_steps=12288,
                         max_frames=300000, completion_milestone=None)
    clock = 0
    count = 0
    command = {}
    decision = 0
    def emit(final=False):
        nonlocal count
        s = snapshot(env.pyboy)
        canvas = Image.new('RGB', (1040,720), '#101820')
        canvas.paste(env.pyboy.screen.image.convert('RGB').resize((640,576), Image.Resampling.NEAREST), (24,94))
        d = ImageDraw.Draw(canvas)
        d.text((24,18), 'HOUSE TO FIRST SMALL KEY', font=title, fill='white')
        d.text((24,55), 'Full continuous route  |  Original speed  |  Guided gameplay with learned local skills', font=fonts[18], fill='#9bc8bc')
        stage = max(i for i,m in enumerate(milestones) if m[0] <= clock)
        d.text((692,98), 'PROGRESSION', font=fonts[18], fill='#9bc8bc')
        for i,(_,name,_) in enumerate(milestones):
            color = '#a9efc7' if i <= stage else '#65737d'
            d.text((692,134+i*30), ('+ ' if i<=stage else '· ')+name, font=fonts[18], fill=color)
        d.text((692,440), 'LIVE STATE', font=fonts[18], fill='#9bc8bc')
        d.text((692,474), f'Health: {s["health"]/8:g} / {s["max_hearts"]} hearts', font=fonts[20], fill='white')
        d.text((692,508), f'Room: {s["room"][0]} / {s["room"][1]:02X} / {s["room"][2]:02X}', font=fonts[18], fill='white')
        d.text((692,540), f'Small Keys: {int(env.pyboy.memory[0xDBD0])}', font=fonts[18], fill='white')
        d.text((692,572), 'Input: '+ (' + '.join(command.get('buttons',[])).upper() or 'RELEASE / WAIT'), font=fonts[16], fill='white')
        d.text((692,608), f'{int(clock/59.72750057)//60:02}:{int(clock/59.72750057)%60:02}  |  Decision {decision+1:,}', font=fonts[18], fill='#9bc8bc')
        note = next((text for frame,text in reversed(notes) if frame<=clock), '')
        d.text((24,686), note, font=fonts[18], fill='#efda9e')
        encoder.stdin.write(canvas.tobytes()); count += 1
        if count==1 or final: canvas.save(OUT/('final.png' if final else 'poster.png'))
    class Tap:
        def __init__(self,boy): self.boy=boy
        def __getattr__(self,key): return getattr(self.boy,key)
        def tick(self,*args,**kwargs):
            nonlocal clock
            result=self.boy.tick(*args,**kwargs); clock+=1
            if clock%2==0:emit()
            return result
    try:
        env.reset(seed=0); clock=env.frames
        env.pyboy=Tap(env.pyboy)
        emit()
        for decision,row in enumerate(rows):
            command=row['command']; info=apply(env,command)[4]
            assert fingerprint(env)==row['fingerprint'], decision
            assert json.loads(json.dumps(snapshot(env.pyboy)))==row['after'], decision
            assert env.frames==row['frame'] and info['events']==row['events'], decision
            if decision%500==0:print(f'Verified {decision}/{len(rows)} commands; {clock/59.72750057:.1f}s rendered',flush=True)
        assert json.loads(json.dumps(env.journal.state()))==journal
        emit(final=True)
        for _ in range(90):emit()
    finally:
        env.close();encoder.stdin.close();code=encoder.wait();log.close()
    assert code==0
    subprocess.run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],check=True)
    manifest=dict(source=str(SOURCE),source_trace_sha256=file_hash(SOURCE/'trajectory.jsonl'),
        video_sha256=file_hash(video),commands=len(rows),frames=count,fps=FPS,
        duration_seconds=count/FPS,all_commands_fingerprint_verified=True,audio=False,
        control='Guided route with learned local skills; cave teacher takes over at decision zero.',
        chapters=[dict(seconds=f/59.72750057,title=n) for f,n,_ in milestones])
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest),flush=True)

if __name__=='__main__':main()
