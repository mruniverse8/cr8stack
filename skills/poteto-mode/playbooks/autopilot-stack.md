### Autopilot-stack

#### Codex execution

In Codex, the [local adapter](../references/local-codex-compatibility.md) overrides conflicting Cursor host assumptions below. Resolve workers through [swarm-sub](../../swarm-sub/SKILL.md) or [swarm-cloud](../../swarm-cloud/SKILL.md), keeping this playbook's phases. A cloud or mixed plan uses the [run-state contract](../../swarm/references/run-state.md). No silent backend fallback.

Apply Autopilot-full's Codex substitutions and preserve this playbook's no-merge boundary. The coordinator integrates accepted Cloud changes into the planned local branches and maintains real dependency bases. Keep a run registry and stop new submissions on pause. Status checks refresh results without lifting the pause or authorizing a push after handoff.

#### Cursor workflow and shared task phases

Run the Autopilot-full playbook, but do not merge.

1. **In place of step 5, stop at verified.** Stop when each PR is verified and green at its current head, then hand the PRs to the operator. After the handoff, nobody pushes without the operator's go. Every loop tick prompt names this file, so each tick sees the no-merge rule.
2. **Stack a PR only when it builds on another PR.** This is the one exception to step 3. Base the PR on the other PR's branch in place of trunk, per **Size and stacks** in `playbooks/opening-a-pr.md`. In place of step 2's rebase onto trunk, each PR rebases onto its parent PR's branch, and the stack root rebases onto trunk. A new head on the lower PR restacks the PRs above it, and a PR whose `git patch-id` the restack leaves unchanged keeps its verdict.

**Reply:** list each PR with its verdict, in place of what merged.
