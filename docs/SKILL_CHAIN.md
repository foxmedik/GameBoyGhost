# Continuing beyond sword acquisition

The learned sword controller now runs as the first skill in a continuous episode.
A scripted planner hands control to a bounded exploration controller after sword
acquisition. No emulator reset or savestate load occurs at this boundary.

This is a prerequisite for work toward Tail Cave, not a Tail Cave solver. The
planner is an explicit two-stage script, and exploration is a deterministic
position-novelty heuristic. Neither is a trained general planner. All runs remain
privilege D because the inherited training environment includes progression
knowledge and assistance. Full-game completion and Tail Cave success remain
unevaluated. The supplied house start already includes the shield.

## Verified behavior

The house development run (`runs/skill-chain-pilot-v3`) acquires the sword in
412 actions and then executes 2,000 exploration actions. Link survives the
2,412-action run with health RAM value 12. The exploration phase visits seven
distinct room identities, including the starting sword beach; these are not
seven newly discovered rooms. It stops with `budget_exhausted`, not success.

A pause at action 900 followed by replay-based resume reproduces all 2,412
actions, the final emulator/observation fingerprint, planner state, room sets,
and final status. Separate integration coverage pauses at action 200 and again
at 430, testing restoration before and after the skill boundary. All 30 project
tests pass, including failure precedence, skill budgets, blocked movement,
damage retreat, and rejection of corrupted checkpoint artifacts.

The two other prepared development starts both acquire the sword and hand off,
but die during exploration. The current explorer is therefore not reliable
across starts:

| Start | Total actions | Rooms visited after acquisition | Outcome |
| --- | ---: | ---: | --- |
| House | 2,412 | 7 | Survived exploration budget |
| Beach | 451 | 3 | Death |
| Approach | 943 | 5 | Death |

Full traces and terminal screenshots are in `runs/skill-chain-final-beach` and
`runs/skill-chain-final-approach`. The long resume comparison is recorded in
`runs/skill-chain-verification-v1.json`, with its pause and resumed outputs in
`runs/skill-chain-final-pause` and `runs/skill-chain-final-resume`.

The first exploration pilot circled within one small area. Committing movement
for up to eight actions allowed it to cross position cells. The second pilot
visited four rooms after acquisition but died at action 1,165. The current
controller records damage locations and reverses movement briefly when hurt;
the successful bounded house run above uses that correction. These are
development iterations, not held-out robustness evidence. Earlier outputs remain
under `runs/skill-chain-pilot-v1` and `runs/skill-chain-pilot-v2`.

## Run and resume

From the project root:

```sh
.venv-ladx/bin/python scripts/run_skill_chain.py --explore-steps 2000

# --stop-after counts total episode actions, including sword acquisition.
.venv-ladx/bin/python scripts/run_skill_chain.py \
  --out runs/my-chain-pause --explore-steps 2000 --stop-after 900
.venv-ladx/bin/python scripts/run_skill_chain.py \
  --resume runs/my-chain-pause
```

Prepared development starts are `--start house`, `--start beach`, and
`--start approach`. Every run uses a fresh output directory. Resume retains the
saved seed, start, exploration budget, and episode identity, with a new run ID
and explicit parent path. Resuming a finished run is rejected.

## Interfaces and artifacts

`src/gameboy_agent/skills.py` defines decoded senses, a controller protocol,
bounded skills, a scripted sequential planner, and serializable exploration
memory. Death takes precedence over simultaneous skill success. Sword skill
failure or timeout stops the chain rather than advancing the planner.

Exploration uses position-cell visits, directional attempts, blocked movement,
and observed damage. It has no supplied map or quest route. It uses only ordinary
movement and A/B controls, selecting the sword's already-equipped slot. It does
not invoke the inherited RAM-based inventory-switch action, although other
inherited harness assistance remains active and disclosed.

Each output directory contains:

- `trajectory.jsonl`: only this process's new steps, with global episode indices,
  before/after senses, action, active skill, reward components, phase, terminal
  flags, run/episode/producer identity, and supervision labels.
- `events.json`: skill outcomes and the planner handoff.
- `checkpoint.json`: full action prefix, planner/explorer memory, provenance,
  budgets, status, and final fingerprint.
- `initial.state`, `emulator.state`, `policy.json`, and `final.png`.
- `manifest.json`: artifact hashes, project/upstream Python source hashes,
  dependency versions, and ROM identity, written last.

Restore checks integrity, then rebuilds the episode from its initial state.
Both the planner's chosen actions and the emulator/observation fingerprint must
match before new actions run. It does not deserialize pickle or treat PyBoy's
emulator snapshot alone as a complete resume. Replay cost grows with episode
length. Checkpoint migration across changed source or dependencies is unsupported.
JSONL remains a diagnostic format; canonical Parquet storage is still pending.

## Next game work

This establishes that skills can be composed and resumed without ending the game
at the first learned objective. Exploration still revisits areas and has only
rudimentary hazard handling. The next gameplay milestone needs reliable
navigation and interaction beyond the beach, followed by a separately verified
Tail Key/Tail Cave task. Room counts and exploration reward cannot certify that
objective.
