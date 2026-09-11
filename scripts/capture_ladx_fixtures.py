"""Replay scripted physical controls; save per-frame diagnostic fixtures.

These are scripted regression cases, never autonomous evaluation trajectories.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import sys

from pyboy import PyBoy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from gameboy_agent.rom_profile import HOOKS as PROFILE_HOOKS, validate_rom
BUTTONS = ('up','down','left','right','a','b','start','select')
HOOKS = {name: (bank, address) for name, (bank, address, _) in PROFILE_HOOKS.items()}
FIELDS = {'indoor':0xDBA5, 'map':0xFFF7, 'room':0xFFF6,
          'x':0xFF98, 'y':0xFF99, 'health':0xDB5A,
          'room_transition':0xC124, 'warp':0xC16B, 'dialog':0xC19F}


def capture(sequence, output, hooks=True, source=None):
    output.mkdir(parents=True, exist_ok=False)
    rom = next(ROOT.glob('*.gbc'))
    validate_rom(rom)
    source = source or ROOT/'references/LADXExperiments/ladx.gbc.state'
    with tempfile.TemporaryDirectory() as temp:
        target = Path(temp)/'game.gbc'
        shutil.copy2(rom,target)
        boy = PyBoy(str(target),window='null')
        boy.set_emulation_speed(0)
        with source.open('rb') as f:
            boy.load_state(f)
        counts = Counter()
        registered = []
        try:
            if hooks:
                for name,(bank,address) in HOOKS.items():
                    boy.hook_register(bank,address,lambda key: counts.update([key]),name)
                    registered.append((bank,address))
            trace=[]
            frame=0
            segments=[]
            for index,segment in enumerate(sequence):
                pressed = segment['buttons']
                if not set(pressed)<=set(BUTTONS) or segment['frames']<1:
                    raise ValueError(segment)
                for button in BUTTONS:
                    (boy.button_press if button in pressed else boy.button_release)(button)
                for _ in range(segment['frames']):
                    counts.clear()
                    boy.tick(1,render=True)
                    frame+=1
                    row={'frame':frame, **{k:boy.memory[v] for k,v in FIELDS.items()},
                         'hooks':dict(counts), 'inventory':list(boy.memory[0xDB00:0xDB0C]),
                         'screen_hash':hashlib.sha256(boy.screen.ndarray.tobytes()).hexdigest(),
                         'ram_hash':hashlib.sha256(bytes(boy.memory[0xC000:0xE000])).hexdigest()}
                    trace.append(row)
                    if counts.get('shield') or counts.get('sword') or counts.get('push'):
                        boy.screen.image.save(output/f'event-{frame:05}.png')
                boy.screen.image.save(output/f'segment-{index:03}.png')
                segments.append({'segment':index,'frame':frame,**{k:row[k] for k in FIELDS},'inventory':row['inventory']})
            with (output/'trace.jsonl').open('w') as f:
                for row in trace:
                    f.write(json.dumps(row)+'\n')
            (output/'sequence.json').write_text(json.dumps(sequence,indent=2)+'\n')
            summary={'supervision':'scripted','human_intervened':True,'ram_edits':False,
                     'completion_evaluated':False,'rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),
                     'initial_state_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                     'frames':frame,'hook_counts':dict(sum((Counter(r['hooks']) for r in trace),Counter())),
                     'segments':segments}
            (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
            for bank,address in registered:
                boy.hook_deregister(bank,address)
            registered.clear()
            with (output/'final.state').open('wb') as f:
                boy.save_state(f)
            print(json.dumps({'frames':frame,'hooks':summary['hook_counts'],'last':segments[-1]}))
            return trace
        finally:
            for bank,address in registered:
                boy.hook_deregister(bank,address)
            boy.stop(save=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('sequence',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--no-hooks',action='store_true')
    parser.add_argument('--state',type=Path)
    args=parser.parse_args()
    capture(json.loads(args.sequence.read_text()),args.output,hooks=not args.no_hooks,source=args.state)


if __name__=='__main__':
    main()
