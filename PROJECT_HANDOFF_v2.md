# Game Boy AI Agent — Build & Collaboration Handoff v2

# v2 Research Update — Incorporated September 2026

This revision incorporates the later PokeRL Discord research logs and changes several build priorities. The overall architecture remains hierarchical and dataset-first, but PufferLib, planner/controller separation, harness neutrality, full resume/replay, curriculum/data-distribution control, and formal vision-vs-senses / teacher-vs-student comparisons are now first-class requirements.

## New Build Decisions

- **PufferLib / pokemonred_puffer is a primary high-performance RL baseline**, alongside SB3/PPO.
- **Planner and controller are separate interfaces from day one.** The planner selects goals/skills; the controller must reliably execute short-horizon behavior.
- **The harness counts as intelligence.** Record a harness-privilege level so game-specific progress knowledge is not mistaken for model capability.
- **Completion is evaluated independently from reward.** Reward remains a training signal; credits/completion is the benchmark.
- **Full experiment resume and deterministic replay move earlier in the build.** Policy weights, optimizer state, emulator state, curriculum state, world memory, and dataset shard position are separate artifacts.
- **Data distribution/curriculum is an explicit experimental variable.** Savestates can train hard skills, but final evaluation remains new-game-to-credits.
- **Vision is an A/B test, not an assumption.** Compare structured RAM/text senses against senses + screenshots under identical tools.
- **Teacher/student is an explicit benchmark.** Compare the large planner against distilled specialists and fast workers.
- **Dreamer/world-model approaches are retained as a baseline branch.**
- **Text extraction/event-driven planning is now supported by prior community experiments**, so it belongs in the reference study.

## Harness Privilege Scale

**A — Minimal:** framebuffer, controls, completion detector.  
**B — Structured senses:** decoded dialogue, inventory, map/room/position and objectively observable RAM-derived state.  
**C — Reusable skills:** navigation, menu operations and interaction primitives.  
**D — Progress hints:** milestone labels, progression graphs or game-specific objective suggestions.

Level D may be useful for curriculum or teacher-data generation, but should not be reported as equivalent to a minimally assisted general-agent result.

## Formal A/B Experiments

1. SB3/PPO vs PufferLib implementation.
2. Pure RL vs hierarchical planner + skills/controller.
3. Structured senses vs structured senses + vision.
4. Deterministic navigation/skills vs learned equivalents.
5. Large teacher vs 7B–14B specialist vs smaller fast worker.
6. Reactive controller vs recurrent controller.
7. Fixed reward design vs alternate reward/curriculum distributions.
8. Known-game performance vs held-out game generalization.

## New Performance / Engineering Targets

Benchmark 8, 16, 24, 32, 48 and 64 headless environments and record emulator SPS, learner SPS, CPU/GPU/RAM, planner queue depth, planner latency, environment wait time and trajectory-write throughput. Do not assume the largest worker count wins.

The collaboration format remains append-only: each machine owns unique producer, run, episode and shard IDs. No two machines write the same training artifact.

## New Reference Repositories

Core and visualization:
- https://github.com/PWhiddy/PokemonRedExperiments
- https://github.com/Xe-Xo/LADXExperiments
- https://github.com/PWhiddy/pokerl-map-viz
- https://github.com/Baekalfen/PyBoy

High-performance RL/environment work:
- https://github.com/drubinstein/pokemonred_puffer
- https://github.com/PufferAI/PufferLib
- https://github.com/PufferAI/pokegym

Alternate/improved Pokemon work:
- https://github.com/CJBoey/PokemonRedExperiments1
- https://github.com/leanke/pokegym
- https://github.com/xinpw8/pokegym
- https://github.com/dvruette/pokemon-emerald-experiments

World-model/language experiments:
- https://github.com/PWhiddy/dreamerv3-poke
- https://github.com/JoshuaPurtell/RedAgentExperiments

Deterministic/TAS reference:
- https://github.com/jonese1234/PokeBotBad

## Research Papers / Leads

- Pokémon Red via Reinforcement Learning (2025): https://arxiv.org/abs/2502.19920
- JARVIS-1: https://arxiv.org/abs/2311.05997
- DreamerV3: https://arxiv.org/abs/2301.04104
- Reward Scale Robustness for PPO via DreamerV3 techniques: https://arxiv.org/abs/2310.17805
- PokeRL: Reinforcement Learning for Pokemon Red (2026): https://arxiv.org/abs/2604.10812
- Additional 2026 paper referenced by the community for a headless/swarm-style project: https://arxiv.org/abs/2603.15563

## Prior Community Findings Worth Preserving

- Long-horizon PPO can make substantial progress, but reward design and data distribution dominate outcomes.
- Policies can exploit reward signals while failing the actual completion objective.
- Recurrent/GRU-style policies showed stronger overall progress in some community ablations.
- Full clears reported by community members came with caveats such as simplifications, state migrations or heavy engineering.
- Modern LLM harness experiments show meaningful multi-badge Pokemon progress, strengthening the case for hierarchical planning.
- Modern experiments are independently testing the same question we care about: whether screenshots add capability beyond structured RAM-derived senses.
- High-speed headless simulation and multi-environment visualization are realistic design targets.

---


**Starting game:** The Legend of Zelda: Link's Awakening DX  
**Long-term goal:** Build a general Game Boy game-playing agent where **game completion** is the headline benchmark.  
**Initial collaborators:** Multiple local high-compute machines contributing compatible trajectories, checkpoints, experiments, and evaluation results.

---

## 1. Project Idea

The project starts from the existing Link's Awakening reinforcement-learning work and the related Pokemon Red ecosystem, but the target is broader:

> Build one reusable agent architecture that can learn to complete multiple Game Boy games, beginning with Link's Awakening DX and later expanding to Pokemon, Mega Man 1–5, Kirby, Metroid II, and other titles.

Link's Awakening is the development laboratory, not the ceiling.

The intended architecture is **hierarchical**:

1. **Emulator + game adapter**
2. **Deterministic tools/skills** where classical algorithms are preferable
3. **Small learned controller(s)** for frame-sensitive or uncertain motor behavior
4. **Fast perception/event detector** when useful
5. **Large multimodal/tool-using planner/teacher**
6. **Persistent world/episodic/semantic memory**
7. **Immutable trajectory collection**
8. **Curated datasets for fine-tuning/distillation**
9. **Shared dashboard + Twitch visualization**
10. **Cross-game completion benchmark**

---

## 2. Reference Repositories

These are the three primary repos to pull first.

### Pokemon Red Experiments
https://github.com/PWhiddy/PokemonRedExperiments

Useful for:
- PyBoy integration
- RL environment patterns
- reward design
- vectorized training
- V2 improvements
- training metrics
- StreamWrapper / broadcast integration
- comparison against later Pokemon RL work

The current README recommends the V2 training path and describes coordinate-based exploration rewards plus map streaming.

### Link's Awakening DX Experiments
https://github.com/Xe-Xo/LADXExperiments

Useful for:
- the existing Link's Awakening environment
- game-specific memory/state work
- first-dungeon training baseline
- the original observation/reward/transition design
- callbacks and visualization hooks

The original Discord thread identified major open issues:
- screen/warp transitions
- better model architecture
- better exploration reward
- better observation encoding

### Pokemon RL Map Visualizer
https://github.com/PWhiddy/pokerl-map-viz

Useful for:
- multi-environment map streaming
- shared live visualization
- StreamWrapper protocol ideas
- multi-machine dashboard inspiration
- Twitch/broadcast presentation layer

The repo is specifically designed to show multiple Pokemon training instances on a shared map.

---

## 3. Get the Reference Repos

Either run:

```bash
chmod +x bootstrap_repos.sh
./bootstrap_repos.sh
```

or clone manually:

```bash
mkdir -p references

git clone https://github.com/PWhiddy/PokemonRedExperiments.git references/PokemonRedExperiments
git clone https://github.com/Xe-Xo/LADXExperiments.git references/LADXExperiments
git clone https://github.com/PWhiddy/pokerl-map-viz.git references/pokerl-map-viz
```

Do **not** commit commercial ROMs, copyrighted game data, secrets, local model weights, or giant trajectory blobs into the project repo.

---

## 4. Suggested Project Directory

```text
gameboy-agent/
├── PROJECT_HANDOFF.md
├── bootstrap_repos.sh
├── references/
│   ├── PokemonRedExperiments/
│   ├── LADXExperiments/
│   └── pokerl-map-viz/
├── src/
│   ├── emulator/
│   ├── adapters/
│   ├── controllers/
│   ├── planners/
│   ├── tools/
│   ├── memory/
│   ├── events/
│   ├── replay/
│   └── dashboard/
├── configs/
├── schemas/
├── scripts/
├── tests/
├── data/
│   ├── raw/
│   ├── curated/
│   └── eval/
├── checkpoints/
├── runs/
└── docs/
```

`references/` should be treated as upstream research material. New project code belongs under `src/` rather than being mixed directly into those repositories until we intentionally decide to fork or vendor something.

---

## 5. Core Architecture

### Layer 1 — Emulator

Responsibilities:
- PyBoy / Game Boy emulation
- controller input
- framebuffer capture
- savestates
- RAM/state inspection
- deterministic replay
- uncapped/headless execution when possible

### Layer 2 — Game Adapter

The adapter exposes the game without embedding its strategy.

Allowed examples:
- framebuffer
- available controls
- reliably decoded dialogue
- objectively observable inventory/player state
- current map/location identifiers
- save/load
- terminal/completion state

Avoid:
- "go get the sword"
- "take the mushroom to the witch"
- dungeon routes
- walkthrough steps
- next-objective labels that directly solve the game

This separation matters for cross-game generalization.

### Layer 3 — Deterministic Tools

Do not force RL to relearn algorithms we already know.

Candidates:
- A* / graph navigation
- menu navigation
- inventory queries
- map lookup
- route following
- interaction primitives
- replay/state inspection

Use learned control where uncertainty or timing makes learning valuable.

### Layer 4 — Learned Motor Controller

Likely small relative to an LLM.

Possible uses:
- combat
- boss fights
- dodging
- precision movement
- dynamic enemies/projectiles
- platforming
- recovery from imperfect route execution

Mega Man 1–5 will stress this layer much harder than Zelda or Pokemon.

### Layer 5 — Fast Perception / Event Detection

Optional smaller model or classifier for:
- dialogue detection
- menu detection
- combat state
- new room/screen
- boss encounter
- death
- stuck condition
- unusual visual event
- escalation trigger

### Layer 6 — Large Planner / Teacher

Initial concept:
- pretrained multimodal/tool-using model
- roughly 27B–70B teacher class
- invoked at meaningful decision points, **not every emulator frame**

Responsibilities:
- long-horizon planning
- interpreting dialogue
- tool selection
- goal decomposition
- hypothesis formation
- failure recovery
- cross-game reasoning

Potential initial comparison:
- strong text/structured-state planner
- strong VLM planner
- existing local models
- later fine-tuned/distilled Game Boy specialists

### Layer 7 — Persistent Memory

Keep memory structured.

**Working memory**
- current objective
- current plan
- current hypothesis

**Episodic memory**
- important attempts
- discoveries
- failures
- outcomes

**World model**
- rooms
- exits
- obstacles
- NPCs
- discovered items
- unknown paths
- known relationships

Prefer a structured graph/database for the world model.

**Semantic memory**
- learned mechanics
- reusable conclusions
- cross-game concepts

Do not treat a giant context window as the memory system.

---

## 6. Parallel Training

The Mac Studio and a friend's machine should behave as **independent producers** that can contribute to the same project.

Parallelism can happen at multiple levels:

### One learner, many environments
Useful for PPO/rollout throughput.

Suggested early scaling benchmark:
- 8 environments
- 16
- 32
- 64
- continue only while steps/sec and learner utilization improve

### Multiple competing experiments
Often more valuable than giving one experiment every available core.

Example:

```text
Experiment A — baseline reward
Experiment B — exploration reward v2
Experiment C — structured-state planner
Experiment D — VLM planner
Experiment E — recurrent controller
Experiment F — alternate memory strategy
```

### Multiple physical machines
Each machine gets unique:
- producer ID
- run ID
- episode IDs
- shard IDs

Machines should never concurrently write the same trajectory/checkpoint file.

---

## 7. Shared Training Data — Design This Before Serious Runs

The project dataset should be treated as a primary artifact.

### Golden rule

**Raw experience is immutable. Curated training datasets are derived from raw experience. Evaluation data is frozen and never silently recycled into training.**

Suggested structure:

```text
data/
├── raw/
│   ├── zelda_ladx/
│   ├── pokemon_red/
│   ├── megaman_1/
│   ├── megaman_2/
│   ├── megaman_3/
│   ├── megaman_4/
│   └── megaman_5/
├── curated/
│   ├── planner_sft/
│   ├── tool_calling/
│   ├── navigation/
│   ├── combat/
│   ├── platforming/
│   ├── recovery/
│   └── completion_runs/
└── eval/
    ├── fixed_seeds/
    ├── regression_cases/
    └── held_out_games/
```

### Store step-level and decision-level data separately

**Step / motor data**
- frame/step
- action
- observation reference
- player state
- enemy/projectile state where available
- damage/death
- reward components

**Planner / semantic data**
- current goal
- relevant world state
- retrieved memory
- available tools
- selected tool
- tool arguments
- tool result
- outcome
- failure reason
- milestone changes

This lets the same raw corpus support both controller training and LLM/VLM fine-tuning.

---

## 8. Canonical Run Metadata

Every run should record:

```text
schema_version
run_id
producer_id
game_id
rom_hash
git_commit
config_hash
emulator_version
adapter_version
planner_model
planner_model_hash
controller_model
controller_model_hash
parent_checkpoint
hardware
os_version
seed
start_time
training/eval mode
human_intervention flag
```

Every derived training sample should be traceable back to:

```text
source_run_id
source_episode_id
source_step_start
source_step_end
```

Never lose provenance.

---

## 9. Recommended Storage Format

### Structured trajectories
**Parquet + Zstandard**

Reasons:
- columnar
- compresses well
- easy to query
- works with PyArrow, Polars, Pandas and Hugging Face Datasets
- supports filtering without loading every field

### Heavy binary material
Examples:
- screenshots
- short video/event clips
- savestates
- large snapshots

Store as:
- content-addressed objects
- `.tar.zst` shards
- or S3-compatible objects

Avoid millions of tiny files if possible.

### Shared storage
Initial options:
- Hugging Face Dataset repository
- S3-compatible object store
- Cloudflare R2
- Backblaze B2
- MinIO / NAS

The code repo should contain **schemas and manifests**, not terabytes of raw training data.

---

## 10. Quality Labels

Every trajectory/sample should be able to carry labels such as:

```text
valid
corrupted
glitch
incomplete
human_intervened
benchmark
teacher_generated
scripted
autonomous
```

Also record supervision source:

```text
autonomous
teacher_model
human
scripted
```

Do not silently mix human-assisted, scripted and autonomous benchmark data.

---

## 11. Rewards and Completion

**Completion / credits reached** should remain the headline success signal.

Intermediate rewards may include:
- exploration
- progression
- item discovery
- new room/map discovery
- combat
- puzzle progress
- novelty

But store components separately:

```text
reward_total
reward_exploration
reward_progression
reward_combat
reward_novelty
reward_completion
```

This makes reward hacking diagnosable after the fact.

Savestates are allowed for curriculum training, but final completion evaluation should start from a legitimate new-game/power-on state.

---

## 12. Deterministic Replay

Day-one requirement.

Any strange behavior should be reproducible.

Record enough to recover:
- ROM hash
- emulator build/config
- initial state
- seed
- button inputs and timing
- relevant state snapshots/checksums
- planner calls/tool calls
- model versions
- rewards/events

The original Zelda experiments produced behaviors such as an unexplained invisible Link. Our goal is that a similar event becomes a replayable regression case instead of a mystery.

---

## 13. Dashboard

The dashboard should serve **research, debugging and Twitch** from one event stream.

### Internal research view
Show:
- all machines
- all active environments
- experiment groups
- steps/sec
- planner latency
- GPU/CPU/memory use
- current milestones
- reward components
- completion statistics
- failures
- checkpoint lineage

### Per-agent view
Show:
- live/sampled Game Boy screen
- map position
- inventory/state
- current objective
- recent events
- concise planner decision
- tool call/result
- controller state
- reward
- replay button

### World/map view
For Zelda:
- Koholint map
- all active Links
- marker by experiment/machine
- event icons
- new areas
- deaths
- milestone events

For Pokemon:
- Kanto map using the existing pokerl-map-viz concepts

For Mega Man:
- stage/room/progress visualization rather than a world map

### Experiment comparison view
Example columns:
- experiment
- active agents
- total steps
- steps/sec
- best milestone
- completion rate
- deaths
- planner calls
- average planner latency
- current best checkpoint

---

## 14. Event Protocol

Training and visualization should be decoupled.

Workers publish structured events; dashboards and recorders subscribe.

Candidate event types:

```text
HEARTBEAT
AGENT_STATE
SCREEN_FRAME
MAP_POSITION
INVENTORY_CHANGE
MILESTONE
PLANNER_REQUEST
PLANNER_DECISION
TOOL_CALL
TOOL_RESULT
REWARD_UPDATE
DEATH
STUCK
GLITCH
NEW_BEST
EPISODE_END
COMPLETION
```

A canonical event bus makes multi-machine collaboration much easier.

The same events can feed:
1. research dashboard
2. Twitch layout
3. immutable dataset recorder
4. alerting
5. replay/indexing services

---

## 15. Twitch Streaming

Do not render dozens of emulator windows individually.

Training workers should run headlessly / uncapped. The dashboard samples their state and renders a viewer-friendly composition.

Suggested broadcast view:
- featured agent
- game map/stage map
- number of active agents
- current objective
- concise planner action
- best milestone
- total training steps
- completion counter
- recent notable events

Automatically feature an agent when it:
- discovers a new area
- obtains a new item
- reaches a boss
- sets a new best
- encounters important dialogue
- escalates to the large planner
- dies unusually
- glitches
- completes the game

OBS/Twitch captures the dashboard, not the training processes.

---

## 16. Model Training / Distillation Path

Do not train a large foundation model from scratch.

Suggested progression:

```text
Large pretrained teacher
        ↓
collect high-quality trajectories
        ↓
curate:
  successful decisions
  failed decisions
  recovery sequences
  tool-use examples
  multimodal examples
        ↓
SFT / LoRA / adapters / preference training
        ↓
7B–14B Game Boy specialist
        ↓
optional 1B–7B fast worker
```

The large model can remain an escalation teacher:

```text
small model confident → act
small model uncertain → teacher
teacher solves → save example
future fine-tune → fewer escalations
```

The target is eventually a **general GameBoy-Agent**, not `zelda-only-7b`.

---

## 17. Benchmark Families

### Zelda — Link's Awakening DX
Stresses:
- exploration
- long-horizon planning
- puzzles
- inventory
- dialogue
- world memory
- dungeon navigation
- combat

Early milestone:
**Full Moon Cello / Dungeon 1 completion**

Final:
**new game → credits**

### Pokemon
Stresses:
- menus
- resource management
- party management
- route progression
- turn-based combat
- dialogue
- very long horizon

Final:
**Hall of Fame / credits**

### Mega Man 1–5
Stresses:
- precision movement
- platforming
- timing
- projectiles
- enemy pattern learning
- boss adaptation
- weapon selection
- cross-game transfer within a closely related series

This family is especially valuable for testing whether motor skills transfer from one game to the next.

---

## 18. Known-Game vs Held-Out Benchmark

Modern pretrained models may already know famous game walkthroughs.

Maintain separate tracks.

### Known-game track
Examples:
- Link's Awakening
- Pokemon Red
- Mega Man

Useful for testing:
- tool use
- control
- memory
- completion engineering

### Held-out/generalization track
Games intentionally excluded from:
- game-specific fine-tuning
- walkthrough/RAG data
- hand-authored strategy

This is the stronger test:

> Can the agent enter a game, infer what matters through interaction, and reach the ending?

---

## 19. Metrics

Headline:
**Games completed**

Also track:
- completion rate
- frames/interactions to completion
- wall-clock time
- training interactions before first completion
- deaths/resets
- planner calls
- planner tokens
- planner latency
- human hints
- game-specific adapter privilege
- training compute
- number of savestate curriculum stages
- zero-shot transfer
- held-out completion
- regression performance after fine-tuning

---

## 20. Initial Work Plan

### Phase 0 — Reference study
- clone the three reference repos
- read architecture and environment code
- identify reusable components
- identify stale dependencies
- document ROM/emulator assumptions
- map existing visualization protocols

### Phase 1 — Reproduce LADX
- create clean reproducible environment
- run existing LADX experiment
- verify PyBoy state
- verify callbacks/viewer
- establish baseline behavior
- do not redesign everything yet

### Phase 2 — Instrumentation
- deterministic replay
- event schema
- canonical run IDs
- Parquet trajectory writer
- immutable shards
- dashboard heartbeat/state feed

### Phase 3 — Fix environment correctness
- warp/screen transition state machine
- stable coordinate/map updates
- regression tests
- crash/state-corruption detection

### Phase 4 — Baseline learning
- reproduce Dungeon 1/boss-room tests
- establish steps/sec
- test 8/16/32/64 environments
- record baseline rewards and milestones

### Phase 5 — General agent layer
- structured world state
- tools
- memory
- planner API
- asynchronous escalation
- compare text planner and VLM planner

### Phase 6 — Zelda completion
- Full Moon Cello reliability
- expand curriculum
- full new-game completion
- independent evaluation seeds

### Phase 7 — Distillation
- curate planner/tool/recovery data
- fine-tune smaller model
- compare teacher vs specialist
- introduce escalation hierarchy

### Phase 8 — Multi-game benchmark
- Pokemon
- Mega Man 1–5
- additional Game Boy titles
- held-out test games

---

## 21. Collaboration Rules

For two or more high-compute contributors:

1. **Same schema versions**
2. **Same run metadata contract**
3. **Unique producer IDs**
4. **Immutable output shards**
5. **No shared writable trajectory files**
6. **Hash every important artifact**
7. **Record git commit/config hash**
8. **Keep raw, curated and eval data separate**
9. **Never train on frozen eval data**
10. **Share checkpoints by immutable version/hash**
11. **Record human assistance**
12. **Make strange failures replayable**
13. **Treat ROMs separately from shared project assets**

A collaborator should be able to clone the project, obtain the legally required game files independently, select an experiment configuration, run it, and produce data that can be merged without manual cleanup.

---

## 22. Immediate First Goal

Do not begin by rewriting the whole project around a 30B VLM.

First establish:

> **Can we reproduce the existing Link's Awakening training environment cleanly, record it deterministically, and understand exactly what it is doing?**

Once that works, modernize it while preserving measurable baselines.

That gives every later experiment a ground truth.

---

## 23. Reference Links

- PokemonRedExperiments  
  https://github.com/PWhiddy/PokemonRedExperiments

- LADXExperiments  
  https://github.com/Xe-Xo/LADXExperiments

- pokerl-map-viz  
  https://github.com/PWhiddy/pokerl-map-viz

- LinkMapViz  
  https://xe-xo.github.io/LinkMapViz/

---

## 24. Working Definition of Success

### Near term
A reproducible modern LADX training setup with:
- clean data
- deterministic replay
- multiple parallel environments
- dashboard
- first-dungeon milestone

### Medium term
A tool-using multimodal planner completes Link's Awakening from a new game, with no hand-coded walkthrough.

### Long term
The same core agent architecture completes an expanding set of Game Boy games, including held-out games, while producing clean reusable data for continuous fine-tuning and distillation.
