"""Render the continuous verified development prefix; never imply door completion.

This is a presentation replay, not a controller, dataset generator, or gate run.
Every action is checked against the source trace while the video is rendered.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from gameboy_agent.checkpoint import fingerprint
from gameboy_agent.progression import snapshot
from gameboy_agent.progression_env import ProgressionEnv
from gameboy_agent.world_memory import file_hash
from run_toadstool_progression import apply

HANDOFF = ROOT / 'runs/tail-cave-room10-state-check-v2/continuation.json'
DEFAULT_OUT = ROOT / 'runs/videos/house-nightmare-route-development-v2'
GAME_FPS = 59.72750057
FPS = GAME_FPS / 2
SIZE = (1280, 720)
BG, PANEL, INK, MUTED, GREEN, AMBER = '#101923', '#192735', '#f3f6fa', '#a9bccc', '#85e0bc', '#ffcf80'
REGULAR = '/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
F = {n: ImageFont.truetype(REGULAR, n) for n in (17, 19, 21, 23, 27, 28)}
B = {n: ImageFont.truetype(BOLD, n) for n in (20, 27, 31, 42)}

# Chapter boundaries are documented development milestones, not evaluation cases.
STAGES = [
    (0, 'House start → the beach', [
        'The supplied house start already has the shield. The first objective is to obtain the sword.',
        'This is the full verified development prefix at normal game speed. Detours and mistakes remain visible.' ]),
    (4869, 'Sword → forest mushroom', [
        'Sword possession is verified. The route now crosses the forest and cave to collect the mushroom.',
        'The aim is a repeatable sequence with checked room and inventory transitions. Playback is not choosing the route.' ]),
    (16078, 'Mushroom → the witch', [
        'The mushroom is acquired. Return through the cave and bring it to the witch for Magic Powder.',
        'These recorded actions document development. They are not automatically approved training examples.' ]),
    (21317, 'Magic Powder → Tarin', [
        'The witch exchange is verified. Return to the forest and use Magic Powder to cure Tarin.',
        'The future learner must handle movement, dialogue, equipment and quest state across the whole sequence.' ]),
    (26262, 'Tarin cured → Tail Key', [
        'The Tarin event is set. Continue to the Tail Key chest and verify that the key was actually collected.',
        'Earlier project experiments used learned local skills. This video replays saved inputs; no model makes live decisions.' ]),
    (27812, 'Tail Key → Tail Cave', [
        'The Tail Key unlocks the dungeon entrance. It is different from the Nightmare Key used for the boss door.',
        'Successful replay shows that these inputs reproduce this run. It does not establish autonomous route success.' ]),
    (33109, 'Tail Cave → first Small Key', [
        'The dungeon is entered. Defeat the first encounter and collect a Small Key for progression inside Tail Cave.',
        'Dungeon movement and combat in this development route are guided. No end-to-end AI completion is claimed.' ]),
    (33888, 'More keys + the Compass', [
        'The first Small Key is secured. Continue through guided encounters toward another key and the Compass.',
        'Deterministic help is part of route development. Later tests must report model-only and assisted success separately.' ]),
    (38289, 'Collecting the dungeon Map', [
        'Continue from the Compass and second-key milestone to the Map chest, then work toward Roc\'s Feather.',
        'A dependable teacher must pass its own reliability gate before it can supply new imitation labels.' ]),
    (39609, 'Map → Roc\'s Feather', [
        'The Map milestone is verified. This section develops the route through hazards and the underground passage.',
        'This is an exploratory trace, with inefficient movement retained. It is not the final optimized route.' ]),
    (45275, 'Roc\'s Feather + health refill', [
        'Roc\'s Feather is obtained. A physical heart pickup restores health before the return route.',
        'Our target requires full health at the opened boss door. Healing during the journey is allowed.' ]),
    (45836, 'Return route + another key', [
        'This run has reached 3/3 hearts, but loses health on the return. That weakness remains visible here.',
        'A separate newer development branch improves this return. It is not spliced into this continuous recording.' ]),
    (48919, 'Approaching the Nightmare Key', [
        'The next Small Key is secured. Follow the upper approach to the raised Nightmare Key chest.',
        'Getting the Nightmare Key is an intermediate milestone. It does not mean the boss door has been reached or opened.' ]),
    (50574, 'Nightmare Key → Rolling Bones', [
        'The Nightmare Key is secured. Cross the next hazards and approach Rolling Bones, the miniboss.',
        'This recording still has only half a heart. It does not satisfy the full-health finish requirement.' ]),
    (52179, 'Verified endpoint: miniboss arrival', [
        'This continuous prefix ends at Rolling Bones. The miniboss is not defeated and the Nightmare door is not open.',
        'Next: finish a reliable, full-health route to the opened boss door. Moldorm comes after that milestone.' ]),
]

INTRO = [
    (10, 'THE PROJECT GOAL', 'House → Nightmare door', [
        'Build a repeatable route from the house to the opened big boss door, with full health and battle-ready equipment.',
        'Today\'s footage reaches the Nightmare Key and Rolling Bones. The door-opening route is still unfinished.',
    ]),
    (13, 'WHAT YOU ARE WATCHING', 'Guided development, replayed', [
        'Saved controller inputs are replayed here. No AI model is making live decisions during this recording.',
        'This is preparation for training: establish the route, qualify the teacher, then collect approved demonstrations.',
        'It is not a trained-model showcase or a completed boss-door run.',
    ]),
]
OUTRO = [
    (12, 'ACTUAL RESULT', 'Nightmare Key: yes. Door open: no.', [
        'The verified sequence ends on arrival at Rolling Bones, with half a heart. The miniboss and boss door remain ahead.',
        'The full-health House → open Nightmare door objective has not been achieved in this recording.',
    ]),
    (13, 'THE TRAINING PLAN', 'Reliable teacher → learned route', [
        'First finish and qualify the full route. Then collect approved sequence examples and freeze a training experiment.',
        'Measure autonomous completion, assisted completion and teacher interventions separately. Keep sealed validation untouched.',
        'This development replay is not evidence that the model has learned the route.',
    ]),
    (20, 'WHAT COMES NEXT', 'Lock down the door. Then Moldorm.', [
        'Target: house → sword → Tarin and Tail Key → Tail Cave items → Nightmare Key → miniboss → open boss door.',
        'Finish outside the boss room at full health, with sword and Roc\'s Feather ready. Boss combat is a separate stage.',
        'Once that route is reliable, Moldorm is next. The Full Moon Cello comes after the boss.',
    ]),
]


def wrapped(draw, text, xy, font, width, fill=INK, gap=7):
    """Draw measured word wrapping, returning the next free baseline."""
    x, y = xy
    line = ''
    for word in text.split():
        candidate = (line + ' ' + word).strip()
        if draw.textlength(candidate, font=font) > width and line:
            draw.text((x, y), line, font=font, fill=fill)
            y += font.size + gap
            line = word
        else:
            line = candidate
    if line:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + gap
    return y


def card(eyebrow, title, paragraphs):
    canvas = Image.new('RGB', SIZE, BG)
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 0, 12, 720), fill=GREEN)
    d.text((76, 64), eyebrow, font=B[20], fill=GREEN)
    y = wrapped(d, title, (76, 120), B[42], 1120, gap=12) + 36
    for text in paragraphs:
        y = wrapped(d, text, (76, y), F[28], 1090, gap=10) + 28
    if y > 630:
        raise ValueError(f'Card text overflows: {title}: {y}')
    d.line((76, 650, 1204, 650), fill='#385060', width=1)
    d.text((76, 675), 'GAMEBOYGHOST  /  DEVELOPMENT RECORDING  /  NO LIVE MODEL DECISIONS', font=F[19], fill=MUTED)
    return canvas


def timestamp(seconds):
    return f'{int(seconds)//60:02}:{int(seconds)%60:02}'


def render(out):
    handoff = json.loads(HANDOFF.read_text())
    sources = [handoff['start']['rom'], handoff['start']['initial_state'], *handoff['replay_segments']]
    for source in sources:
        if file_hash(ROOT / source) != handoff['sha256'][source]:
            raise ValueError(f'Source hash mismatch: {source}')
    rows = [json.loads(line) for source in handoff['replay_segments']
            for line in (ROOT / source).read_text().splitlines()]
    if [r['decision'] for r in rows] != list(range(len(rows))):
        raise ValueError('The source commands are not one contiguous sequence')
    if rows[-1]['frame'] != handoff['final']['frame']:
        raise ValueError('Source endpoint differs from the handoff')
    out.mkdir(parents=True, exist_ok=False)
    cards = [(duration, card(eye, title, paras)) for duration, eye, title, paras in INTRO + OUTRO]
    for i, (_, canvas) in enumerate(cards):
        canvas.save(out / f'card-{i+1}.png')
    cards[0][1].save(out / 'poster.png')
    video = out / 'house-nightmare-route-development-annotated.mp4'
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    log = (out / 'encoding.log').open('w')
    encoder = subprocess.Popen([ffmpeg, '-y', '-loglevel', 'error', '-f', 'rawvideo',
        '-pix_fmt', 'rgb24', '-s', '1280x720', '-r', str(FPS), '-i', '-', '-an',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', str(video)], stdin=subprocess.PIPE, stderr=log)
    count, clock, start_clock, decision = 0, 0, 0, 0
    command = {}
    milestones_seen = {}
    began = time.monotonic()
    env = ProgressionEnv(ROOT / handoff['start']['rom'], ROOT / handoff['start']['initial_state'],
        max_steps=len(rows) + 100, max_frames=300000, completion_milestone=None)
    cached = {}

    def write_frame(canvas):
        nonlocal count
        encoder.stdin.write(canvas.tobytes())
        count += 1

    def still(duration, canvas):
        raw = canvas.tobytes()
        nonlocal count
        for _ in range(round(duration * FPS)):
            encoder.stdin.write(raw)
            count += 1

    def base(stage, note_index):
        key = stage, note_index
        if key in cached:
            return cached[key].copy()
        canvas = Image.new('RGB', SIZE, BG)
        d = ImageDraw.Draw(canvas)
        d.text((24, 15), 'BUILDING THE HOUSE → NIGHTMARE DOOR ROUTE', font=B[31], fill=INK)
        d.rounded_rectangle((24, 57, 1256, 88), radius=6, fill='#344536')
        d.text((36, 62), 'RECORDED INPUT REPLAY  •  NO LIVE AI DECISIONS  •  GUIDED DEVELOPMENT', font=B[20], fill=GREEN)
        d.rounded_rectangle((688, 105, 1256, 678), radius=12, fill=PANEL)
        d.text((712, 122), f'ROUTE CHAPTER {stage+1:02} / {len(STAGES):02}', font=F[19], fill=GREEN)
        y = wrapped(d, STAGES[stage][1], (712, 158), B[27], 516, gap=8)
        y = wrapped(d, STAGES[stage][2][note_index], (712, max(y + 20, 239)), F[23], 513, gap=8)
        assert y < 455, (stage, y)
        d.line((712, 460, 1232, 460), fill='#385060')
        d.text((712, 476), 'OBSERVED GAME STATE', font=F[19], fill=GREEN)
        d.text((712, 623), 'BOSS DOOR: PENDING', font=B[20], fill=AMBER)
        d.text((712, 651), 'Moldorm follows the completed route.', font=F[19], fill=MUTED)
        d.text((24, 692), 'NORMAL SPEED  /  CONTINUOUS GAMEPLAY  /  DEVELOPMENT EVIDENCE, NOT AUTONOMOUS SUCCESS', font=F[17], fill=MUTED)
        cached[key] = canvas
        return canvas.copy()

    def emit(final=False):
        s = snapshot(env.pyboy)
        stage = max(i for i, entry in enumerate(STAGES) if entry[0] <= clock)
        milestones_seen.setdefault(stage, count / FPS)
        note = int((clock - STAGES[stage][0]) / GAME_FPS / 16) % 2
        canvas = base(stage, note)
        canvas.paste(env.pyboy.screen.image.convert('RGB').resize((640, 576), Image.Resampling.NEAREST), (24, 105))
        d = ImageDraw.Draw(canvas)
        health = s['health'] / 8
        d.text((712, 507), f'Health: {health:g} / {s["max_hearts"]} hearts', font=F[23], fill=AMBER if health < 1 else INK)
        d.text((712, 541), f'Room {s["room"][0]}:{s["room"][1]:02X}:{s["room"][2]:02X}   |   Small Keys: {env.pyboy.memory[0xDBD0]}', font=F[21], fill=INK)
        buttons = ' + '.join(command.get('buttons', [])).upper() or 'RELEASE / WAIT'
        d.text((712, 575), f'{timestamp((clock-start_clock)/GAME_FPS)}   |   Command: {buttons}', font=F[19], fill=MUTED)
        write_frame(canvas)
        if final:
            canvas.save(out / 'final-gameplay.png')
        elif stage not in saved_stages:
            canvas.save(out / f'chapter-{stage+1:02}.png')
            saved_stages.add(stage)

    saved_stages = set()

    class Tap:
        def __init__(self, boy): self.boy = boy
        def __getattr__(self, key): return getattr(self.boy, key)
        def tick(self, *args, **kwargs):
            nonlocal clock
            # ProgressionEnv advances exactly one emulator frame per call.
            if args and args[0] != 1:
                raise ValueError('Unexpected multi-frame emulator tick')
            if kwargs.get('count', 1) != 1:
                raise ValueError('Unexpected multi-frame emulator tick')
            result = self.boy.tick(*args, **kwargs)
            clock += 1
            if (clock - start_clock) % 2 == 0:
                emit()
            return result

    try:
        for duration, canvas in cards[:len(INTRO)]:
            still(duration, canvas)
        env.reset(seed=0)
        clock = start_clock = env.frames
        gameplay_start = count / FPS
        env.pyboy = Tap(env.pyboy)
        emit()
        for decision, row in enumerate(rows):
            command = row['command']
            info = apply(env, command)[4]
            assert fingerprint(env) == row['fingerprint'], f'Fingerprint at {decision}'
            assert json.loads(json.dumps(snapshot(env.pyboy))) == row['after'], f'Snapshot at {decision}'
            assert env.frames == row['frame'] and info['events'] == row['events'], f'Timing/events at {decision}'
            assert clock == env.frames, f'Render clock at {decision}'
            if decision % 500 == 0:
                print(f'Verified {decision:,}/{len(rows):,} inputs; gameplay {timestamp((clock-start_clock)/GAME_FPS)}; render elapsed {time.monotonic()-began:.0f}s', flush=True)
        assert json.loads(json.dumps(snapshot(env.pyboy))) == handoff['final']['state']
        assert [env.pyboy.memory[a] for a in range(0xDBCC, 0xDBD1)] == handoff['final']['dungeon_items']
        emit(final=True)
        gameplay_end = count / FPS
        outro_start = count / FPS
        for duration, canvas in cards[len(INTRO):]:
            still(duration, canvas)
    finally:
        env.close()
        encoder.stdin.close()
        code = encoder.wait()
        log.close()
    assert code == 0, 'Video encoding failed'
    subprocess.run([ffmpeg, '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True)
    chapters = [dict(seconds=0, title='The goal and the disclosure')]
    # Combine the short refill/return boundary and the last-frame arrival with
    # their neighbors so upload chapters are distinct and at least 10s long.
    chapters += [dict(seconds=seconds, title=("Roc's Feather, refill and return" if i == 10 else STAGES[i][1]))
                 for i, seconds in milestones_seen.items() if i not in (11, 14)]
    chapters += [dict(seconds=outro_start, title='Actual result and the plan for Moldorm')]
    assert all(b['seconds'] - a['seconds'] >= 10 for a, b in zip(chapters, chapters[1:]))
    manifest = dict(schema='annotated-development-video-v1', source_handoff=str(HANDOFF.relative_to(ROOT)),
        sources_sha256={p: file_hash(ROOT / p) for p in sources}, renderer_sha256=file_hash(Path(__file__)),
        video_sha256=file_hash(video), commands_verified=len(rows),
        all_commands_fingerprint_snapshot_timing_events_verified=True,
        frames=count, fps=FPS, resolution=list(SIZE), duration_seconds=count/FPS,
        gameplay_start_seconds=gameplay_start, gameplay_end_seconds=gameplay_end,
        source_first_frame=start_clock, source_final_frame=clock, source_segments=len(handoff['replay_segments']),
        control='Recorded input replay of guided development; no live model inference.',
        gameplay_continuous=True, gameplay_speed=1, audio=False, training_labels_generated=0,
        autonomous_completion_claimed=False, teacher_qualified=False, boss_door_opened=False,
        endpoint='Nightmare Key acquired; fresh Rolling Bones arrival; 0.5/3 hearts.', chapters=chapters)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    chapter_text = '\n'.join(f'{timestamp(c["seconds"])} {c["title"]}' for c in chapters)
    (out / 'chapters.txt').write_text(chapter_text + '\n')
    (out / 'youtube-description.txt').write_text(
        'Building the House-to-Nightmare-Door Route | Guided Development, Not Autonomous AI\n\n'
        'This is a full, normal-speed replay of our verified development progress in Link\'s Awakening DX. '
        'Saved controller inputs drive the gameplay; no AI model is making live decisions in this recording. '
        'Earlier project experiments used learned local skills, but this replay is not an autonomous-model demonstration.\n\n'
        'We start from the supplied house state with the shield already acquired, obtain the sword, collect the mushroom, '
        'trade it for Magic Powder, cure Tarin, get the Tail Key, and enter Tail Cave. Inside, we progress through Small Keys, '
        'the Compass, Map, Roc\'s Feather and Nightmare Key, ending on arrival at Rolling Bones. '
        'The gameplay is continuous; the separate newer health-preserving branch is not spliced in.\n\n'
        'Important: the boss door is NOT opened in this video. Rolling Bones is still undefeated at the endpoint, '
        'and Link has half a heart. This does not meet our full-health completion goal.\n\n'
        'The objective is to establish a reliable house-to-open-Nightmare-door route, finishing outside the boss room '
        'at full health with the sword and Roc\'s Feather ready. This work prepares the training process: '
        'finish the route, pass the teacher reliability gate, collect approved demonstrations, then train and evaluate '
        'a learner. This development replay is not approved training data, and no new route training happens in the video. '
        'Guided success, autonomous success and teacher interventions will be reported separately. '
        'Sealed validation remains untouched.\n\n'
        'Once that route is locked down, Moldorm is the next separate challenge, followed by the Full Moon Cello.\n\n'
        'Burned-in annotations; silent video.\n\n' + chapter_text + '\n')
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    render(args.out.resolve())
