"""Create provenance-tracked pre-sword starts using only fixture buttons."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from pyboy import PyBoy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.rom_profile import validate_rom
from gameboy_agent.transitions import read_phase,world_ready

def build(output):
    output.mkdir(parents=True,exist_ok=False)
    source=ROOT/'references/LADXExperiments/ladx.gbc.state'
    sequence_path=ROOT/'configs/fixtures/house_to_sword_and_push.json'
    sequence=json.loads(sequence_path.read_text())
    rom=next(ROOT.glob('*.gbc'));validate_rom(rom)
    stages={7823:'sword_approach',5039:'beach_route'}
    manifest={'schema_version':'scripted-curriculum-v1','supervision':'scripted_start',
              'ram_edits':False,'source_state_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'sequence_sha256':hashlib.sha256(sequence_path.read_bytes()).hexdigest(),'stages':[]}
    with tempfile.TemporaryDirectory() as tmp:
        target=Path(tmp)/'game.gbc';shutil.copy2(rom,target)
        boy=PyBoy(str(target),window='null');boy.set_emulation_speed(0)
        try:
            with source.open('rb') as f:boy.load_state(f)
            frame=0
            for segment in sequence:
                for button in ('up','down','left','right','a','b','start','select'):
                    (boy.button_press if button in segment['buttons'] else boy.button_release)(button)
                for _ in range(segment['frames']):
                    boy.tick(1,render=True);frame+=1
                    if frame in stages:
                        assert boy.memory[0xDB4E]==0 and 1 not in boy.memory[0xDB00:0xDB0C]
                        assert world_ready(read_phase(boy))
                        name=stages[frame];path=output/f'{name}.state'
                        with path.open('xb') as f:boy.save_state(f)
                        boy.screen.image.save(output/f'{name}.png')
                        manifest['stages'].append({'name':name,'frame':frame,'state_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                                   'phase':read_phase(boy),'dialog':boy.memory[0xC19F],
                                                   'sword_level':boy.memory[0xDB4E]})
                if frame>=max(stages):break
        finally:boy.stop(save=False)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
if __name__=='__main__':print(json.dumps(build(Path(sys.argv[1]))))
