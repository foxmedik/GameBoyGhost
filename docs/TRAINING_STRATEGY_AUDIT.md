# Training strategy audit — 11 September 2026

**Recommendation: pause the manual cliff/sword tuning loop and return to a measurable game-progression milestone.** The work has produced useful controllers and unusually strong replay evidence, but continuing to perfect the same coordinate routes is not the best-supported next use of effort. We have not established that this loop is the blocker to the next game milestone.

This audit uses the canonical handoff, current runtime/training code, experiment reports and recorded resource counters. No training, new gameplay evaluation, policy change or reserved-evaluation access was performed. The recommendation is a proposed next work program, not an experiment already launched.

## 1. Intended goal versus current optimization

The canonical goal is a reusable hierarchical agent that progresses through and eventually completes games. The near-term handoff includes a first-dungeon milestone; medium-term success is Link's Awakening completion from a new game without a hand-coded walkthrough. It explicitly allows planners, tools, deterministic skills and learned controllers. It does not require every motor decision to be learned before further progression.

| Layer | Intended outcome | What is currently demonstrated |
| --- | --- | --- |
| Game progress | First dungeon, then full completion | Sword acquisition; no measured Tail Cave progression or completion result |
| Planning | Choose useful goals and recover/replan | A scripted sword→novelty-exploration sequence; fixed external goals in navigation tests |
| Navigation learning | Useful control across relevant states/goals | 9/9 familiar four-goal routes using exact-final-goal specialists |
| Robustness | Continue after changed states | 34/48 safe completions in the new physical-perturbation panel |
| Verification | Trust the observed outcomes | Strong hashes, continuous replay, feature equality and resume checks |

The selected navigator remains `experimental_not_default`. The default `SequentialPlanner` still acquires the sword and then runs scripted novelty exploration. Selecting a navigation checkpoint has not, by itself, integrated a game-progression planner.

The recent optimizer objective is **behavior cloning**: movement cross-entropy plus a smaller button-classification loss, previously combined with parent-retention and action-margin terms. Environment reward, dungeon progress and credits do not drive these optimizer updates. Failed rollouts inform manually chosen new data/experiments; there is no automated game-completion learning loop here. Earlier PPO experiments are a separate, real part of project history.

Sources: [canonical handoff](../PROJECT_HANDOFF_v2.md), [runtime skill sequence](../src/gameboy_agent/skills.py), [route trainer](../scripts/train_navigation_routes.py), [specialist trainer](../scripts/train_cliff_specialists.py), [cliff-correction trainer](../scripts/train_cliff_correction_v2.py).

## 2. What worked and should be retained

- Environment correctness, ROM matching, deterministic replay and explicit assistance labels prevent phantom gains. Do not dismantle this infrastructure.
- The sword controller is a usable prerequisite: 70/70 tested starts, including 12 separately reserved sword-validation cases. These remain fixed-ROM savestate perturbations, not whole-game generalization.
- Rejecting damaging/regressing candidates protected the selected controller.
- Collecting fresh features on actual learner trajectories, and verifying the following leg continuously, produced the most convincing recent correction.
- Frozen v7 fallback and return weights prevented unrelated weight drift during the final cliff fix. This is an effective containment technique.
- The stress panel was informative: all 12 controls matched historical traces; 43/48 shifted cases completed, 34 safely, nine with damage and five with timeouts. Setup caused no damage. Eight first-damage events and three timeouts were on the return goal.

The work was useful bootstrap and diagnostic engineering. Its value should not be confused with proof that further iterations of the same process are the best route to completion.

## 3. Why the process started chasing individual failures

**The proxy became the working objective.** A loop of arbitrary known coordinates became a promotion target without a demonstrated connection to the next story/dungeon milestone. We accumulated acceptance conditions around that loop, rather than measuring whether the agent could do something new in the game.

**The scope narrowed while the score improved.** The final runtime matches complete final goals E2 (64,64) and E2 (36,121) to separate networks. Other goals use v7. This is explicitly labeled, legitimate specialization; it is not evidence of arbitrary-goal obstacle planning. Adding another expert whenever a new coordinate fails would scale maintenance and data requirements with the test set.

**Varied-state and continuous-handoff tests arrived too late.** A clean arrival can leave a poor combat state for the next action. Earlier return regressions already showed this. We should have required perturbation and continuation coverage before treating route correction as a reusable capability. Replay establishes reproducibility, not distributional coverage.

**Our corrective collection was reactive and labor-intensive.** We often inspected a failure, adjusted teacher waypoints or prefixes, trained, and reran broad preservation panels. Training states shifted again under the new policy. This resembles manual dataset aggregation, but lacks a fixed, broad task distribution, automated collection policy, and an explicit stopping rule.

**Some supervision was unnecessarily difficult to imitate.** Original navigation targets came from successful endpoints of scripted/random exploration, not an expert pursuing those goals. Successful paths can contain reversals and wall bumps. Shortest-suffix selection resolves a label conflict but can splice actions into a state the source trajectory did not visit. We physically demonstrated both valid and uncovered splices. Higher label agreement did not reliably imply live success: v9 improved teacher fit yet fell from six complete routes to three.

**We optimized an efficiency detail prematurely.** Sword-suppression experiments reduced a teacher's swing count, but learned/coupled variants lost navigation success or safety. Until there is a reliable progression baseline, fewer swings is a secondary diagnostic, not the primary research direction. Its current pause is appropriate.

**We lacked a mechanism-level decision rule.** A plateau led to another repair or loss change. We did not consistently specify in advance which result would implicate planning, observation/history, teacher quality, or optimization—and cause us to stop working on the others.

I contributed to this drift by treating local failure reports as the next task and presenting completion of the original routes too strongly as resolution of the capability. The accurate claim was always narrower: those frozen routes passed, under the stated harness and exact-goal architecture.

## 4. What the resource evidence supports

The reproducible [evidence ledger](../reports/training-process-audit.json) covers **13 recent candidate experiments**: route v1–v9, two sword candidates and two cliff-specialist candidates. They contain **1,872 candidate local cases**, at least **2,112 documented local rollouts including explicit baseline reruns**, and **117 candidate route rollouts**. This excludes many teacher searches, earlier recovery/PPO experiments, chains and independent replays. These are workload counts, not independent samples of generalization.

| Recorded resource | Evidence | Interpretation |
| --- | --- | --- |
| Large corpus | 16,777,216 actions; 8,133 episodes | Collection, not 16.8M expert examples or optimizer steps |
| Collection active time | 2,389.6 seconds, about 39.8 minutes | Adequate demonstrated throughput for that collection workload |
| Committed collection output | 5.316 GiB | Corpus size is not currently evidence of a storage bottleneck |
| Collection process-CPU counter | 50,260 seconds, about 13.96 core-hours | Reported supervisor counter, not a complete project cost total |
| One navigation network | 132,104 parameters | A small model; selected fallback plus two experts totals 396,312 |
| Earlier fixed PPO batch | Four completed candidates, two failed; about 3.57 hours batch wall time | Historical bounded comparison; no completion result |

The 16.8M-action corpus was generated from three base savestates with learned sword acquisition followed by scripted/random exploration. Its hindsight-navigation cache uses 346,536 training rows. Large volume does not ensure coverage of coherent goal-directed detours or safe handoffs. The final cliff update used 447 corrected/preserved cliff rows plus 14 local-anchor rows; their information content mattered more than accumulating more exploration volume.

**Cost-accounting limitation:** recent candidate plans do not supply a unified train/collect/evaluate wall-time, core-hour, assistant-effort, token or monetary ledger. I cannot honestly assign a total dollar cost or prove that human effort dominates compute by a particular ratio. Epoch counts are not comparable across the large retention trainer and small specialist datasets. File timestamps are not a substitute for measured runtime.

My judgment is that objective design, coverage and manual iteration are the immediate bottlenecks—not demonstrated lack of model size or hardware. Do not buy more compute, regenerate the same broad corpus, or launch a large PPO sweep on the strength of the current evidence.

Sources: [collection status](../runs/data-workset-16m-v1/status.json), [collection benchmark](DATA_WORKSET.md), [curated-data semantics](CURATED_DATA.md), [first navigation experiment](NAVIGATION_EXPERIMENT.md), [older PPO batch](../runs/overnight-fixed-20260910-090710/status.json).

## 5. Recommended training goal and next work

**Proposed next milestone:** verify acquisition of the Tail Key and entry into Tail Cave from a post-sword state; then demonstrate the same progression continuously from the supplied house start. The subsequent milestone is the first dungeon/Full Moon Cello. Verify milestone conditions against the matched game implementation before scoring them. These are intermediate steps toward the canonical completion goal, not a substitute for eventual new-game-to-credits evaluation.

First establish a **progression baseline without optimizer updates**. Use the current skills behind an explicit goal manager, recording what selects each goal, when control stalls, when recovery/replanning occurs, and every human/teacher intervention. Keep the controller's supplied final goal separate from planner decisions. A planner may reuse observed transitions, blocked-edge memory and bounded recovery; it should not silently embed the manually demonstrated cliff route as a general solution. A hand-authored route can be a separately labeled upper-bound/teacher baseline, not the unassisted agent claim.

This answers the missing question: **what actually blocks the next game milestone?** It may be goal selection, task knowledge, interaction, local control or combat. Do not assume the most recently observed cliff failure is the critical path.

Once a blocker is demonstrated, choose the smallest experiment that distinguishes explanations:

| Finding | Next intervention | Avoid |
| --- | --- | --- |
| Goals are poor or detours require persistent knowledge | Goal manager with observed-map/transition memory and explicit replanning | More labels for the same final coordinate |
| Competent teacher succeeds broadly; learner fails on its own states | Automated, bounded learner-state collection and teacher corrections, including safe following-leg outcomes | More unfiltered random exploration |
| Same available input needs incompatible actions | Inspect timing/observability and test a small history or recurrent variant against a matched baseline | Assuming recurrence is needed from raw conflicting labels alone |
| Good inputs/teacher, but learner cannot fit or transfer | One controlled model/loss comparison, with fixed data and compute | Unbounded sweeps or adding a specialist per failure |
| Learned control adds no useful advantage over a simple baseline | Keep the simpler controller for progression; retain learning as a separate research track | Requiring every component to be neural |

Learner-induced distribution shift is a well-established issue in sequential imitation. Automated aggregation is a plausible next learning method *if* we have a reliable corrective teacher and a useful task distribution; our current teacher does not provide a general safety oracle. The theoretical guarantees do not automatically apply to these approximate scripted corrections. [Ross, Gordon & Bagnell, 2011](https://proceedings.mlr.press/v15/ross11a.html).

## 6. A bounded experiment charter

The following caps and thresholds are **proposed engineering choices**, not observed performance guarantees or an approved compute run:

1. **First work block: milestone/integration baseline, zero optimizer updates.** Verify the progress detector; freeze initial states, supplied information, action budget and intervention rules; establish the selected system's result. Freeze a disjoint development validation group before changing the system.
2. **One targeted comparison.** Compare the selected system with one explicit planning/recovery alternative under the same observation and assistance contract. Use, for example, 20 development setups and 20 separate validation setups, grouped by complete physical initialization. Keep a 4,096-action progression budget unless a preregistered baseline calibration shows it is inappropriate. Changing it creates a new protocol for all arms.
3. **Provisional success criterion:** at least 18/20 validation setups reach the verified milestone alive without runtime human rescue, plus preserved existing regression behavior. Record damage, resets, physical frames, actions and wall time separately. Twenty related setups are an engineering gate, not a statistical claim of universal reliability.
4. **Only then consider training.** Cap the next learning investigation at three fixed candidates and one million newly generated emulator actions, with a strategy review at the first cap. Count teacher search and evaluation actions too. Do not launch it as part of this audit.
5. **Stop/reassess rules:** no optimizer run before the teacher/task contract is verified; no second sweep if the same failure mechanism persists; no additional exact-goal expert without explaining why it advances the milestone and how it will be maintained. If a candidate only improves familiar cases, record regression improvement and do not claim transfer.

The learning target should be a reusable short-horizon skill over a defined state/goal distribution, with an explicit failure/replan interface. The whole-system target should be verified progression per unit of wall time and intervention effort. These are separate scoreboards.

## 7. Evaluation and workflow changes

- **Three evidence lanes:** training/correction data; visible development/regression cases; locked validation. The 144 local cases, nine routes and inspected stress panel belong to visible development/regression. Preserve the 96 reserved navigation specifications; confirm their scope before using them as a future test. They are not automatically a Tail Cave or whole-game benchmark.
- **Test composition and perturbations early.** A local success is insufficient if the next leg starts unsafely. Include arrival distributions, timing changes and room transitions before training, not only after a clean demonstration passes.
- **Keep zero-damage regressions, but define the gameplay objective deliberately.** Zero damage is a useful existing preservation condition. Whole-game progression also requires measuring survival, resource use and completion; do not let swing count or a blanket zero-hit proxy silently replace the objective. Any changed promotion criterion needs its own explicit protocol; do not retroactively relax a failed experiment.
- **Use staged evaluation.** Reject clear failures on a small frozen diagnostic suite before running the entire preservation suite. Finalists still receive full live preservation and replay/resume checks. Reuse immutable baseline results only when policy, harness, cases, budgets and source identities match; rerun when relevant loading/runtime code changes.
- **Measure before parallelizing.** Add monotonic wall time, process CPU, emulator actions/frames, unique setup counts, teacher attempts, correction rows, failures and outcome-per-cost. Benchmark the actual current evaluator at a few worker counts if profiling identifies it as a bottleneck. The older 32-worker collection optimum is not evidence that 32 is best for neural evaluation.
- **Consolidate routine machinery.** Prefer one versioned training/evaluation driver with data/config manifests over another cloned script per candidate. Preserve historical snapshots. Optimize prefix restoration only after proving full emulator/host-state equivalence; exact replay exists for a reason.
- **Use seed checks when choosing a learning method.** One fixed seed is useful for debugging, but a claimed algorithm improvement should survive multiple training seeds under the same task split and resource budget. This does not mean repeating every tiny fix across a large seed sweep. [Henderson et al., 2018](https://ojs.aaai.org/index.php/AAAI/article/view/11694).

## 8. Decision recorded by this audit

Keep the selected specialist and every artifact. Pause further navigation optimizer experiments while the next task contract is established; sword reduction remains paused. Do not automatically turn the 14 stress failures into another patch-training batch. The research-focus file records this pause and the proposed progression-first direction; it is not a runtime toggle.

No policy/runtime files, held-out evaluation definitions, or training data were changed. No new optimizer updates, gameplay experiments, commits or uploads occurred. This audit does not claim that a planner, recurrence, RL or aggregation has already solved the remaining problem. It identifies the next decision that offers more information and closer alignment with the actual goal than another isolated cliff repair.
