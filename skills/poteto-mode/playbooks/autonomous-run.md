### Autonomous run

#### Codex execution

In Codex, the [local adapter](../references/local-codex-compatibility.md) overrides conflicting Cursor host assumptions below. Resolve workers through [swarm-sub](../../swarm-sub/SKILL.md) or [swarm-cloud](../../swarm-cloud/SKILL.md), keeping this playbook's phases. A cloud or mixed plan uses the [run-state contract](../../swarm/references/run-state.md). No silent backend fallback.

State the predicate, backend, dependencies, and acceptance checks before submission. Use the saved registry and decision trail for Cloud or mixed work. An active coordinator can wait for and read Cloud results through the desktop tools; Cursor `/loop` and a persistent Cloud coordinator are not implied.

When a coordinator stops, submitted Cloud tasks may keep working but no new dependencies are promised to launch. Session pickup runs swarm-check, preserves explicit pauses, reconciles uncertain submissions, verifies available results, and resumes only within the original grant. Retain real exit checks and never relax missing evidence into success.

#### Cursor workflow and shared task phases

**You own the exit condition. Define done, then drive to it without stopping.**

1. State the exit condition as a checkable predicate before the first iteration (tests green, repro fixed, all N PRs merged, pixel-diff zero).
2. Pick the wake mechanism using Cursor's `/loop` command (a built-in, not a pstack skill). An event to watch (CI, a merge, a ref advancing) gets a watcher subagent that wakes you on the event, with a long time-based heartbeat as fallback. No event gets a fixed-interval heartbeat sized to when the result is worth re-checking. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section.
3. Each iteration makes the smallest change the evidence justifies, verifies it against the predicate, commits if it advanced, discards changes that didn't help. Belt-and-suspenders that "might help" gets reverted, not left to ride.
   Sequence the work via the **sequence-verifiable-units** principle skill, verifying each unit before the next instead of batching checks at the end.
4. Mid-run discoveries that support the goal are yours. Address broken skills, related bugs, flaky verifiers, review noise, tooling failures, orphaned follow-ups, and fixable drift yourself via poteto-mode. Put out-of-band fixes in their own PR. Do not park reversible work for the human or use `AskQuestion`. Surface only irreversible actions, genuine product or preference calls no experiment can settle, or a real dead end. Keep the predicate as the main drive, and return to it after each side fix.
5. Checkpoint every iteration via the **show-me-your-work** skill, a row for what changed and whether the predicate moved.
6. Stop when the predicate is met. A plateau is not a stop, so keep going and pivot your approach to push past it. Surface a genuine dead end rather than spinning, and never relax the predicate to declare victory.

**Reply:** the exit condition, iterations run, what landed, what was discarded, final predicate state.
