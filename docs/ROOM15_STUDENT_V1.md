# Room 0x15 autonomous student v1

The first autonomous room-15 student is rejected. It cleared 13/20 fresh continuous house-start cases, below the frozen 18/20 acceptance gate, and cleared 2/4 half-heart cases, below the required 4/4. Every case had an exact replay. The teacher entered room `0x15`, then the student issued every room-15 command with no fallback.

The model trained on 7,586 examples from 19 clean teacher trajectories and reached 92.95% action agreement on 6,146 examples from 15 held-out clean trajectories. This offline score did not transfer to reliable closed-loop control.

All seven failures exhausted the 700-command budget. They did not die at termination. Five settled while holding shield movement against the lower-left pair, one oscillated around a remaining upper-right Zol, and one stalled near a lower-right Zol. The model frequently repeated either `B` or `Left+B` for its final 100 commands. This identifies recovery states that imitation from successful traces did not cover.

The candidate is preserved at `runs/room15-student-v1-candidate/candidate.pt`; its frozen gate is `runs/room15-student-v1-gate-v5/summary.json`. The prior verifier-only gate attempts are preserved but are not performance evidence: v1 omitted the replay idle input, v2 used concurrent emulators, v3 used a process-spawn setup that did not terminate, and v4 compared normalized replay state against in-memory tuple state. The v5 evaluator fixes these issues and is the only scored student result.

All seven frozen failure states then received a state-checked teacher recovery in continuous replay: 1,106 teacher commands across seven successful exact replays. One recovery took four raw damage; the other six were damage-free. These are the first valid on-policy correction candidates. They still require a separately frozen extraction, split, and student acceptance gate before training.

The frozen correction candidate (v2) added 1,034 usable recovery rows to v1's 7,586 clean training rows, then ran a new 20-case autonomous panel at unused offsets 46–65. It cleared 7/20 cases and 2/4 half-heart cases, below the same 18/20 and 4/4 gates. All 20 replays were exact. V2 is rejected: naively mixing the concentrated correction states into the clean imitation data made closed-loop behavior worse, even though offline held-out agreement remained 92.86%. The reliable teacher remains selected.

No existing autonomous model was replaced. The selected 43/43 teacher remains the reliable controller. The next experiment is a frozen, continuous on-policy correction collection from these seven student-created states; only teacher recoveries that complete and replay exactly may become labels. Existing sealed validation remains untouched.
