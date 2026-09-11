"""Persistent knowledge boundaries and source-backed route determinism."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from gameboy_agent.world_memory import WorldMemory

FIXTURES=ROOT/'runs/progression-interface-v1-verified'


class MemoryTests(unittest.TestCase):
    def setUp(self):
        if not (FIXTURES/'house/manifest.json').exists():
            self.skipTest('Requires verified local progression fixtures')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.out=Path(self.tmp.name)

    def imported(self):
        m=WorldMemory();m.import_verified_fixture(FIXTURES/'house');return m

    def test_directed_route_no_invented_return(self):
        m=self.imported()
        route=m.route([1,16,163],[0,0,242])
        self.assertEqual(route['status'],'observed_route')
        self.assertEqual(len(route['legs']),12)
        self.assertFalse(route['execution_validated'])
        self.assertEqual(m.route([0,0,242],[1,16,163])['status'],'unknown_route')
        self.assertEqual(m.route([0,0,242],[0,0,65])['status'],'unknown_route')

    def test_roundtrip_reproduces_every_room_pair_query_and_evidence(self):
        m=self.imported();path=self.out/'memory.json';m.save(path);loaded=WorldMemory.load(path)
        rooms={tuple(map(int,o['room'].split(':'))) for o in m.observations.values()}
        for a in rooms:
            for b in rooms:self.assertEqual(m.route(a,b),loaded.route(a,b))
        self.assertEqual(m.version,loaded.version)
        self.assertEqual(loaded.verify_evidence(),len(m.observations))

    def test_import_order_and_duplicate_import_do_not_change_memory(self):
        a,b=WorldMemory(),WorldMemory()
        for start in ('house','beach','approach'):a.import_verified_fixture(FIXTURES/start)
        for start in ('approach','beach','house'):b.import_verified_fixture(FIXTURES/start)
        self.assertEqual(a.version,b.version)
        prior=a.version;a.import_verified_fixture(FIXTURES/'house');self.assertEqual(prior,a.version)

    def test_inheritance_has_history_but_no_live_episode_state(self):
        m=self.imported();child=m.next_generation()
        self.assertEqual(child.parent,m.version)
        self.assertEqual(child.observations,m.observations)
        self.assertNotIn('inventory',child.payload())
        self.assertNotIn('milestones',child.payload())
        self.assertNotIn('health',child.payload())
        self.assertEqual(child.route([1,16,163],[0,0,242]),m.route([1,16,163],[0,0,242]))
        child.import_verified_fixture(FIXTURES/'beach')
        self.assertEqual(len(m.sources),1)

    def test_tampering_fails_before_import_changes_memory(self):
        shutil.copytree(FIXTURES/'house',self.out/'fixture')
        (self.out/'fixture/trajectory.jsonl').write_text('{}\n')
        m=WorldMemory();prior=m.version
        with self.assertRaisesRegex(ValueError,'integrity'):m.import_verified_fixture(self.out/'fixture')
        self.assertEqual(m.version,prior)
        path=self.out/'memory.json';m.save(path)
        value=json.loads(path.read_text());value['payload']['generation']=200
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'integrity'):WorldMemory.load(path)

    def test_opposing_movement_observations_survive_without_wall_inference(self):
        m=WorldMemory();m.sources['synthetic-test-only']={}
        row=json.loads((FIXTURES/'house/trajectory.jsonl').read_text().splitlines()[0])
        stationary=deepcopy(row);stationary['after']=deepcopy(stationary['before'])
        m.ingest_row('synthetic-test-only',stationary)
        row['decision']=1;m.ingest_row('synthetic-test-only',row)
        result=m.movement_evidence(row['before']['room'],[row['before']['x']//8,row['before']['y']//8],'down')
        self.assertTrue(result['mixed_outcomes'])
        self.assertEqual(result['passability'],'unknown')
        self.assertEqual([len(v) for v in result['outcomes'].values()],[1,1])

    def test_damage_keeps_event_position_and_never_assigns_enemy_cause(self):
        m=WorldMemory();m.sources['synthetic-test-only']={}
        row=json.loads((FIXTURES/'house/trajectory.jsonl').read_text().splitlines()[0])
        row['events']=[dict(id=0,frame=10,kind='health_lost',room=row['before']['room'],
            position=[30,40],details={'before':24,'after':20})]
        m.ingest_row('synthetic-test-only',row)
        event=next(o for o in m.observations.values() if o['kind']=='damage')
        self.assertEqual(event['details']['position'],[30,40])
        self.assertEqual(event['details']['raw_loss'],4)
        self.assertIsNone(event['details']['cause'])


if __name__=='__main__':unittest.main()
