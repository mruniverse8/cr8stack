### Pause safely

#### Codex execution

In Codex, the [local adapter](../references/local-codex-compatibility.md) overrides conflicting Cursor host assumptions below. Resolve workers through [swarm-sub](../../swarm-sub/SKILL.md) or [swarm-cloud](../../swarm-cloud/SKILL.md), keeping this playbook's phases. A cloud or mixed plan uses the [run-state contract](../../swarm/references/run-state.md). No silent backend fallback.

Persist the scheduling pause and reason through the [run-state contract](../../swarm/references/run-state.md) before starting another item. Record cloud task IDs, submitted and uncertain launches, pending dependencies, retrieved evidence, branches, and integration state in the durable effort directory. Keep the existing TSV decision format.

The pause stops new submissions. Native subagents may be interrupted through actual host tools; Cloud tasks may continue. Do not claim Cloud cancellation without a supported command and confirmed result. Helpers do not commit, push, apply patches, or create PRs; retain changes in their existing isolated worktrees and report any source-control action that needs separate authority. This overrides the automatic WIP commit in the Cursor steps below.

Leave a durable checkpoint, not a sole copy in `/tmp`. Print the remaining active workers, accepted and pending results, ready-but-paused work, and the exact run directory for Session pickup. A status check preserves the pause. A later resume requires the user's explicit request.

#### Cursor workflow and shared task phases

**You own a clean stop. Leave a checkpoint a cold-start agent can resume from.** This is explicit only. On "keep going", "going to bed, keep going", or "don't stop", do not pause.

1. Stop at a safe boundary. Finish the current atomic step or back out of it. Start nothing new, and cancel any nested subagents.
2. Take no irreversible action to pause. No PR and no push unless you already had one out.
3. Make the work durable. Commit uncommitted edits as one clear `wip:` commit on the current branch so nothing is lost. If the tree is broken, say so in the commit body in one line.
4. Write the resume note off-context. Capture intent, what you were doing, progress and what's verified, current state, next steps, key files, and gotchas. For the compaction trigger write it to a file like `/tmp/<slug>-resume.md`. If a show-me-your-work trail exists, point at it instead of duplicating it.

**Reply:** where you are in the loop, what's on disk versus still in your head (paths, no diff dumps), the commits you made and whether the tree is clean, and the first action on resume. This is a pause, not a final report.
