"""Upload only a checksum-verified dataset release, then verify remote files."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from huggingface_hub import HfApi,hf_hub_download


def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def upload(release,repo,report):
    release=Path(release).resolve();checks=json.loads((release/'checksums.json').read_text())
    allowed=set(checks)|{'checksums.json'}
    actual={str(p.relative_to(release)) for p in release.rglob('*') if p.is_file()}
    if actual!=allowed:raise ValueError('Release contains missing or unexpected files')
    for name,h in checks.items():
        p=release/name
        if p.is_symlink() or not p.resolve().is_relative_to(release):raise ValueError('Release path escapes folder')
        if p.suffix.lower() not in {'.parquet','.json','.md','.txt'}:raise ValueError('Unexpected release artifact type')
        if digest(p)!=h:raise ValueError(f'Checksum mismatch: {name}')
    api=HfApi();info=api.repo_info(repo,repo_type='dataset')
    print('UPLOADING',len(allowed),'verified files to',repo,flush=True)
    result=api.upload_folder(repo_id=repo,repo_type='dataset',folder_path=str(release),allow_patterns=sorted(allowed),
        commit_message='Publish verified LADX collection v1: 16,777,216 actions')
    revision=result.oid
    remote=api.repo_info(repo,repo_type='dataset',revision=revision,files_metadata=True)
    files={p.rfilename:p for p in remote.siblings};assert allowed<=files.keys()
    expected={**checks,'checksums.json':digest(release/'checksums.json')}
    verified=0
    with tempfile.TemporaryDirectory() as tmp:
        for name,h in expected.items():
            f=files[name];assert f.size==(release/name).stat().st_size
            if f.lfs:
                remote_hash=f.lfs.sha256 if hasattr(f.lfs,'sha256') else f.lfs['sha256']
                assert remote_hash==h,name
            else:
                local=hf_hub_download(repo_id=repo,repo_type='dataset',filename=name,revision=revision,local_dir=tmp)
                assert digest(local)==h,name
            verified+=1
    output=dict(repo_id=repo,revision=revision,verified_files=verified,public=not info.private,
        rows=json.loads((release/'manifest.json').read_text())['rows'],remote_hashes_match=True)
    Path(report).write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--release',required=True);p.add_argument('--repo',required=True);p.add_argument('--report',required=True)
    a=p.parse_args();upload(a.release,a.repo,a.report)
