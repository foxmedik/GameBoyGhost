"""Export committed episodes and curated indexes without ROM/runtime assets."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import pyarrow as pa
import pyarrow.parquet as pq
from gameboy_agent.dataset import sha256
BATCH=ROOT/'runs/data-workset-16m-v1'
CURATED=ROOT/'data/curated/ladx-navigation-v1'


def public_table(table):
    index=table.schema.get_field_index('producer_id')
    values=['producer-'+hashlib.sha256(v.encode()).hexdigest()[:20] for v in table['producer_id'].to_pylist()]
    return table.set_column(index,table.schema.field(index),pa.array(values))


def export_shard(job):
    number,entries,out=job;out=Path(out);relative=f'raw/shard-{number:05}.parquet';dest=out/relative
    writer=None;rows=0;records=[]
    try:
        for group,item in enumerate(entries):
            source=BATCH/item['source_path'];assert sha256(source)==item['source_sha256']
            meta=json.loads((source.parent/'manifest.json').read_text());assert sha256(source.parent/'manifest.json')==item['manifest_sha256']
            t=public_table(pq.read_table(source));assert len(t)==item['rows']
            if writer is None:writer=pq.ParquetWriter(dest,t.schema,compression='zstd',compression_level=3)
            writer.write_table(t,row_group_size=len(t))
            records.append({**item,'release_shard':relative,'release_row_group':group,'release_row_start':rows,
                'start':meta['start'],'seed':meta['seed'],'epsilon':meta['epsilon'],'outcome':meta['status'],
                'sword_acquired':meta['sword_acquired'],'action_sha256':meta['action_sha256']})
            rows+=len(t)
    finally:
        if writer:writer.close()
    # Every output row group corresponds to exactly one complete source episode.
    output=pq.ParquetFile(dest);assert output.num_row_groups==len(entries)
    for group,item in enumerate(entries):
        expected=public_table(pq.read_table(BATCH/item['source_path']))
        assert output.read_row_group(group).equals(expected,check_metadata=False),'Logical export mismatch'
    return dict(path=relative,sha256=sha256(dest),bytes=dest.stat().st_size,rows=rows,episodes=records)


def export(out,workers=8):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);(out/'raw').mkdir();(out/'metadata').mkdir();(out/'curated').mkdir()
    cm=json.loads((CURATED/'manifest.json').read_text());inventory_path=CURATED/'source-inventory.json'
    assert sha256(inventory_path)==cm['artifacts']['source-inventory.json']
    inventory=json.loads(inventory_path.read_text());assert len(inventory)==8133 and sum(e['rows'] for e in inventory)==16777216
    retired=json.loads((ROOT/'runs/navigation-live-correction-v3/plan.json').read_text())['retired_cohorts']
    retired=set(retired)
    jobs=[(i//128,inventory[i:i+128],str(out)) for i in range(0,len(inventory),128)];shards=[];episodes=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(export_shard,jobs):
            episodes+=result.pop('episodes');shards.append(result);print('VERIFIED SHARD',len(shards),len(jobs),flush=True)
    mapping={e['source_path']:e for e in episodes}
    for e in episodes:e['development_retired']=e['cohort_id'] in retired
    pq.write_table(pa.Table.from_pylist(episodes),out/'metadata/episodes.parquet',compression='zstd')
    for split in ['train','dev']:
        (out/'curated'/split).mkdir()
        for p in sorted((CURATED/split).glob('*.parquet')):
            relative=str(p.relative_to(CURATED));assert sha256(p)==cm['artifacts'][relative]
            t=pq.read_table(p);sources=t['source_path'].to_pylist();cohorts=t['cohort_id'].to_pylist()
            t=t.append_column('release_shard',pa.array([mapping[s]['release_shard'] for s in sources]))
            t=t.append_column('release_row_group',pa.array([mapping[s]['release_row_group'] for s in sources],type=pa.int32()))
            t=t.append_column('development_retired',pa.array([c in retired for c in cohorts]))
            pq.write_table(t,out/'curated'/relative,compression='zstd')
    meta=json.loads((BATCH/inventory[0]['source_path']).parent.joinpath('manifest.json').read_text())
    (out/'metadata/observation-layout.json').write_text(json.dumps(meta['observation_layout'],indent=2)+'\n')
    (out/'metadata/schema.txt').write_text(str(pq.read_schema(out/shards[0]['path'])))
    for name in ['data-workset-16m-v1-final-verification.json','data-workset-16m-v1-quality-summary.json','curation-v1-verification.json']:
        # Publish aggregate findings without private machine paths.
        data=json.loads((ROOT/'runs'/name).read_text())
        def scrub(v):
            if isinstance(v,dict):return {k:scrub(x) for k,x in v.items()}
            if isinstance(v,list):return [scrub(x) for x in v]
            if isinstance(v,str):return v.replace(str(ROOT),'PROJECT_ROOT')
            return v
        (out/'metadata'/name).write_text(json.dumps(scrub(data),indent=2)+'\n')
    manifest=dict(version='ladx-collection-v1',source_batch_id=cm['source_batch_id'],rows=sum(s['rows'] for s in shards),episodes=len(episodes),
        raw_shards=len(shards),shards=shards,curation_version=cm['schema'],curated_segments=cm.get('segments'),
        retired_cohorts=sorted(retired),reserved_evaluation_included=False,harness_privilege='D',completion_evaluated=False,
        source_inventory_sha256=sha256(inventory_path),exporter_sha256=sha256(__file__),
        transform='producer_id pseudonymized with SHA-256 prefix; all other raw values unchanged; episodes retained including duplicates',
        verification='Every exported raw row group compared value-for-value against its transformed committed source episode',
        source_code='https://github.com/foxmedik/GameBoyGhost',dataset='https://huggingface.co/datasets/foxmedik/GameBoyGhost-LADX')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copy2(ROOT/'docs/HF_DATASET_CARD.md',out/'README.md')
    checks={str(p.relative_to(out)):sha256(p) for p in sorted(out.rglob('*')) if p.is_file()}
    (out/'checksums.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(dict(rows=manifest['rows'],episodes=len(episodes),shards=len(shards),bytes=sum(p.stat().st_size for p in out.rglob('*') if p.is_file()))),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=8);a=p.parse_args();export(a.out,a.workers)
