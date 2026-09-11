"""Build versioned world memory from the three verified development traces."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.world_memory import WorldMemory,file_hash


def run(out):
    began=time.monotonic()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_world_memory.py')
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful() or result.skipped:raise AssertionError('Memory tests must pass without skips')
    out.mkdir(parents=True,exist_ok=False)
    interface=json.loads((ROOT/'reports/progression-interface-v1.json').read_text())
    if interface['status']!='passed':raise ValueError('Interface evidence has not passed')
    memory=WorldMemory()
    for start in ('house','beach','approach'):
        memory.import_verified_fixture(ROOT/interface['run_directory']/start)
    observed=memory.verify_evidence()
    memory.save(out/'generation-0.json')
    loaded=WorldMemory.load(out/'generation-0.json')
    child=loaded.next_generation();child.save(out/'generation-1.json')
    rooms=sorted({tuple(map(int,o['room'].split(':'))) for o in memory.observations.values()})
    queries=[]
    for origin in rooms:
        for target in rooms:
            query=memory.route(origin,target)
            assert query==loaded.route(origin,target)==child.route(origin,target)
            queries.append(dict(origin=origin,target=target,result=query))
    (out/'route-queries.json').write_text(json.dumps(queries,indent=2)+'\n')
    examples=dict(house_to_sword=memory.route([1,16,163],[0,0,242]),
                  sword_to_house=memory.route([0,0,242],[1,16,163]),
                  sword_to_tail_key=memory.route([0,0,242],[0,0,65]))
    (out/'example-routes.json').write_text(json.dumps(examples,indent=2)+'\n')
    counts=Counter(o['kind'] for o in memory.observations.values())
    report=dict(schema='world-memory-validation-v1',status='passed',tests_run=result.testsRun,
        source_traces=len(memory.sources),observations=observed,counts=dict(counts),
        unique_rooms=len(rooms),route_queries_identical=len(queries),
        every_observation_rederived_from_hashed_trace=True,generation_0=memory.version,
        generation_1=child.version,example_route_legs=len(examples['house_to_sword']['legs']),
        return_route_status=examples['sword_to_house']['status'],
        tail_key_route_status=examples['sword_to_tail_key']['status'],
        episode_state_inherited=False,live_navigation_integration=False,
        inheritance_efficiency_evaluated=False,new_emulator_actions=0,optimizer_updates=0,
        reserved_evaluation_used=False,wall_seconds=round(time.monotonic()-began,3),
        output=str(out.relative_to(ROOT)),
        code_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in
                    [ROOT/'src/gameboy_agent/world_memory.py',ROOT/'tests/test_world_memory.py',Path(__file__)]},
        artifacts={p.name:file_hash(p) for p in out.iterdir() if p.is_file()})
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'reports/world-memory-v1.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'runs/world-memory-v1')
    run(parser.parse_args().out.resolve())
