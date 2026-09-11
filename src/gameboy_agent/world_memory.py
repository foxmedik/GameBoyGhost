"""Evidence-backed world knowledge, independent of episode possession/state.

Edges are directed observations, not guaranteed routes or inferred prerequisites.
Movement failures remain attempts, never permanent collision labels.
"""
from collections import deque
from copy import deepcopy
import hashlib
import json
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def room_key(room):
    if len(room) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in room):
        raise ValueError('Room must contain three byte integers')
    return ':'.join(str(v) for v in room)


def context(state):
    # Historical conditions of an observation; never live agent possession.
    return {key: deepcopy(state[key]) for key in
            ('inventory', 'sword', 'toadstool', 'powder', 'tail_key', 'tarin',
             'tail_door_status', 'trade_item', 'health')}


class WorldMemory:
    schema = 'world-memory-v1'

    def __init__(self, *, generation=0, parent=None):
        self.generation = generation
        self.parent = parent
        self.sources = {}
        self.observations = {}

    def payload(self):
        return dict(schema=self.schema, generation=self.generation, parent=self.parent,
                    sources=deepcopy(self.sources), observations=deepcopy(self.observations))

    @property
    def version(self):
        return digest(self.payload())

    def save(self, path):
        with Path(path).open('x') as stream:
            stream.write(canonical(dict(payload=self.payload(), sha256=self.version))+'\n')

    @classmethod
    def load(cls, path):
        envelope = json.loads(Path(path).read_text())
        value = envelope['payload']
        if digest(value) != envelope['sha256'] or value['schema'] != cls.schema:
            raise ValueError('Memory integrity/schema mismatch')
        if set(value) != {'schema','generation','parent','sources','observations'}:
            raise ValueError('Unexpected memory fields; episode state cannot be inherited')
        result = cls(generation=value['generation'], parent=value['parent'])
        result.sources = value['sources']
        result.observations = value['observations']
        for key, observation in result.observations.items():
            if digest(observation) != key or observation['evidence']['source'] not in result.sources:
                raise ValueError('Invalid observation evidence')
        return result

    def next_generation(self):
        child = WorldMemory(generation=self.generation+1, parent=self.version)
        child.sources = deepcopy(self.sources)
        child.observations = deepcopy(self.observations)
        return child

    def ingest_row(self, source, row):
        """Idempotent ingestion; caller must register verified source provenance."""
        if source not in self.sources:
            raise ValueError('Register trace evidence before ingesting observations')
        before, after = row['before'], row['after']
        decision = row['decision']
        base = dict(source=source, decision=decision, line=decision+1, frame=row['frame'])

        def add(kind, room, details, *, event=None):
            evidence = {**base, **({'event_id':event['id'], 'frame':event['frame']} if event else {})}
            observation = dict(kind=kind, room=room_key(room), details=details,
                               conditions=context(before), evidence=evidence)
            self.observations[digest(observation)] = observation

        # One location per action is evidence of presence, not map completeness.
        add('presence', before['room'], dict(position=[before['x'],before['y']]))
        for event in row['events']:
            kind = event['kind']
            if kind == 'room_transition':
                origin, target = event['details']['from_room'], event['details']['to_room']
                # Action boundary positions are only a bracket around a crossing.
                # Do not claim a precise door/ledge coordinate from this trace.
                add('connection', origin, dict(to_room=room_key(target),
                    action_start=dict(room=before['room'], position=[before['x'],before['y']]),
                    settled_arrival=dict(room=event['room'], position=event['position']),
                    action_end=dict(room=after['room'], position=[after['x'],after['y']]),
                    buttons=row['command']['buttons'], reverse_verified=False,
                    prerequisites='unknown', location_precision='action_boundary_bracket'),event=event)
            elif kind == 'health_lost':
                add('damage',event['room'],dict(position=event['position'],
                    raw_loss=event['details']['before']-event['details']['after'],
                    cause=None,buttons=row['command']['buttons']),event=event)
            elif kind in ('dialogue_observed','sword_acquired','toadstool_acquired',
                          'powder_available','raccoon_cured','tail_key_acquired',
                          'tail_cave_opened','tail_cave_entered','trade_item_changed'):
                add('landmark_observation',event['room'],dict(position=event['position'],
                    event_kind=kind,text=event['text'],details=event['details'],
                    repeatability='unknown'),event=event)
        directions = [b for b in row['command']['buttons'] if b in ('up','down','left','right')]
        # Only compare stationary/moving outcomes within settled, dialogue-free
        # gameplay. Animation or entities can still explain no displacement.
        world = lambda s: (s['phase']['gameplay']==11 and s['phase']['subtype']==7
                           and s['phase']['scroll']==0 and s['phase']['sequence']==4
                           and s['phase']['palette']==0 and s['dialog_state']==0)
        if len(directions)==1 and before['room']==after['room'] and world(before) and world(after):
            distance = abs(after['x']-before['x'])+abs(after['y']-before['y'])
            add('movement_attempt',before['room'],dict(position=[before['x'],before['y']],
                cell=[before['x']//8,before['y']//8],direction=directions[0],
                displacement=distance,outcome='no_displacement' if distance==0 else 'displaced',
                cause=None,buttons=row['command']['buttons']))

    def import_verified_fixture(self, directory):
        directory = Path(directory).resolve()
        manifest = json.loads((directory/'manifest.json').read_text())
        for name, expected in manifest['artifacts'].items():
            if Path(name).name != name or file_hash(directory/name) != expected:
                raise ValueError(f'Fixture integrity mismatch: {name}')
        for required in ('trajectory.jsonl','result.json','journal.json'):
            if required not in manifest['artifacts']:
                raise ValueError(f'Missing fixture artifact: {required}')
        result = json.loads((directory/'result.json').read_text())
        if result.get('exact_action_replay') is not True:
            raise ValueError('Only replay-verified traces may seed this memory')
        trace = directory/'trajectory.jsonl'
        rows = [json.loads(line) for line in trace.read_text().splitlines()]
        if [r['decision'] for r in rows] != list(range(len(rows))) or len(rows)!=result['steps']:
            raise ValueError('Non-contiguous trace decisions')
        events = [e for row in rows for e in row['events']]
        if events != json.loads((directory/'journal.json').read_text())['events']:
            raise ValueError('Trace events differ from journal evidence')
        for row in rows:
            if any(e['decision']!=row['decision'] or e['frame']>row['frame'] for e in row['events']):
                raise ValueError('Event outside its action evidence')
        source = file_hash(trace)
        # Commit only after the whole import validates; import order is immaterial.
        staged = WorldMemory(generation=self.generation,parent=self.parent)
        staged.sources=deepcopy(self.sources);staged.observations=deepcopy(self.observations)
        staged.sources[source] = dict(trace=str(trace),sha256=source,
            manifest_sha256=file_hash(directory/'manifest.json'),
            result_sha256=file_hash(directory/'result.json'),replay_verified=True,
            assistance=result['assistance'],steps=len(rows))
        for row in rows:staged.ingest_row(source,row)
        self.sources,self.observations=staged.sources,staged.observations
        return source

    def connections(self):
        return sorted(((key,o) for key,o in self.observations.items() if o['kind']=='connection'),
                      key=lambda pair:(pair[1]['room'],pair[1]['details']['to_room'],pair[0]))

    def route(self, origin, target):
        """Deterministic shortest observed room chain, not a motor action tape."""
        origin,target=room_key(origin),room_key(target)
        queue=deque([(origin,[])])
        visited={origin}
        while queue:
            room,path=queue.popleft()
            if room==target:
                return dict(status='observed_route',rooms=[origin]+[p['to_room'] for p in path],
                            legs=path,execution_validated=False,conditions_checked=False)
            for key,obs in self.connections():
                next_room=obs['details']['to_room']
                if obs['room']==room and next_room not in visited:
                    visited.add(next_room)
                    queue.append((next_room,path+[dict(from_room=room,to_room=next_room,
                        observation=key,evidence=obs['evidence'],conditions=obs['conditions'])]))
        return dict(status='unknown_route',rooms=[],legs=[],explored_graph_rooms=sorted(visited),
                    reason='No observed directed chain; no reverse connections assumed.')

    def movement_evidence(self, room, cell, direction):
        outcomes={kind:[] for kind in ('no_displacement','displaced')}
        for key,obs in sorted(self.observations.items()):
            d=obs['details']
            if (obs['kind']=='movement_attempt' and obs['room']==room_key(room)
                    and d['cell']==list(cell) and d['direction']==direction):
                outcomes[d['outcome']].append(key)
        return dict(outcomes=outcomes,mixed_outcomes=all(outcomes.values()),passability='unknown')

    def verify_evidence(self):
        """Re-derive every observation from immutable source traces."""
        rebuilt=WorldMemory(generation=self.generation,parent=self.parent)
        for source,provenance in sorted(self.sources.items()):
            trace=Path(provenance['trace'])
            if file_hash(trace)!=source:raise ValueError('Trace evidence changed')
            rebuilt.import_verified_fixture(trace.parent)
        if rebuilt.payload()!=self.payload():raise ValueError('Memory differs from source evidence')
        return len(self.observations)
