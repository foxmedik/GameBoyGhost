"""Prepare an honest local development snapshot. Does not commit or upload."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
ARTIFACTS=(
    'configs/house_to_boss_door_v2.json',
    'configs/house_boss_door_checkpoint_v1.json',
    'docs/HOUSE_TO_BOSS_DOOR_FULL_HEALTH.md',
    'reports/full-health-route-development-v1.json',
    'reports/house-boss-door-route-progress-v1.json',
    'reports/nightmare-key-route-smoke-v1.json',
)
SOURCES=(
    'src/gameboy_agent/battle_ready_endpoint.py',
    'src/gameboy_agent/boss_door_endpoint.py',
    'src/gameboy_agent/full_health_route.py',
    'src/gameboy_agent/boss_door_route.py',
    'src/gameboy_agent/nightmare_key_route.py',
    'scripts/continue_tail_cave_guided.py',
    'scripts/prepare_route_checkpoint.py',
    'tests/test_battle_ready_endpoint.py',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(output):
    output=Path(output).resolve()
    phase=json.loads((ROOT/ARTIFACTS[0]).read_text())
    report=json.loads((ROOT/'reports/full-health-route-development-v1.json').read_text())
    if report.get('exact_replay') is not True:
        raise ValueError('Finish exact replay before packaging development evidence')
    for name in ARTIFACTS+SOURCES:
        path=ROOT/name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f'Unsafe or missing allowlisted artifact: {name}')
    output.mkdir(parents=True,exist_ok=False)
    for name in ARTIFACTS:
        dest=output/'evidence'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest)
    source=dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                working_tree_clean=not bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
                limitation='Base commit does not pin uncommitted work. Commit the corresponding source before a qualified release.',
                files={name:digest(ROOT/name) for name in SOURCES})
    (output/'source_snapshot.json').write_text(json.dumps(source,indent=2)+'\n')
    manifest=dict(kind='development_evidence_snapshot',schema_version=1,
                  training_rows=0,model_checkpoint=None,published=False,
                  full_health_door_proven=phase['completion']['route_proof_verified'],
                  teacher_qualified=phase['completion']['full_route_teacher_qualified'],
                  training_started=phase['completion']['training_started'],
                  qualified_release_ready=False,
                  blocked_by=['full-health door proof missing','whole-route teacher unqualified','training dataset/model not produced','source checkpoint commit not pinned'],
                  hf_repository='foxmedik/GameBoyGhost-LADX',
                  proposed_remote_prefix='releases/house-boss-door-full-health-v1/development',
                  files=list(ARTIFACTS),source_snapshot='source_snapshot.json')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'README.md').write_text('''# House → Boss Door: full-health route development\n\nThis is development evidence, not a trained policy or a completed full-health route.\n\nThe project has guided Nightmare Key acquisition and a miniboss arrival. The new feather return reaches the next key room at 24/24 health, compared with 8/24 previously, with 578 fewer emulated frames in this development comparison. The next guarded encounter timed out. Full-health boss-door completion, full-route teacher qualification, and model training are still pending.\n\nTraining rows: **0**. Model checkpoint: **none**. No sealed evaluation cases, ROMs, or emulator savestates are included. The source snapshot identifies local files; a corresponding Git commit must be pinned before a qualified release. No upload is performed by the preparation script.\n''')
    checks={str(p.relative_to(output)):digest(p) for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'checksums.json').write_text(json.dumps(checks,indent=2)+'\n')
    return dict(path=str(output),files=len(checks)+1,kind=manifest['kind'],qualified_release_ready=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    print(json.dumps(prepare(parser.parse_args().output),indent=2))
