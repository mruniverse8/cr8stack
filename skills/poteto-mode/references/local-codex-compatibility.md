# Local Codex compatibility

This installation preserves Cursor pstack workflows with a Codex adapter. This file and each Codex execution block take precedence over conflicting Cursor instructions below them. Cursor follows the upstream sections unchanged.

## Choose execution before delegation

Read [swarm](../../swarm/SKILL.md) before fan-out. `$swarm-sub` uses native Codex collaboration tools in the current execution environment. `$swarm-cloud` uses the loaded Codex desktop tools to submit and retrieve independent Cloud tasks. `$swarm` defaults to Cloud through the desktop tools. Explicit native requests and genuinely local-only work use native subagents. Announce the backend. A blocked backend stays blocked; never silently switch it.

A native subagent is not an independent cloud machine. Cloud tasks have separate workspaces and cannot read local absolute paths, unpushed work, local transcripts, or the parent's secrets and tools by implication. Follow the [worker contract](../../swarm/references/worker-contract.md) and [cloud transport](../../swarm/references/codex-cloud.md). Read the named leaf skill from the installed sibling directory. `/name` in Cursor prose means `$name` or an explicit Codex request, not a shell command.

Translate Task/Agent only at the worker boundary. Keep the caller's design, review, or investigation phases; do not reroute the entire playbook recursively through swarm. A poteto-agent is an ordinary worker given accessible poteto-mode instructions. Native workers use the available collaboration schema, ownership boundaries, and actual concurrency limits, never invented `subagent_type`, `environment`, or `cloud_base_branch` fields. Cloud workers receive self-contained briefs and cloud-accessible source and evidence pointers.

## Models and host capabilities

Cursor model slugs and `~/.cursor/rules/pstack-models.mdc` configure Cursor only. Native swarm workers follow [swarm-sub](../../swarm-sub/SKILL.md), including its explicit task-based model and effort routing. Use fresh self-contained workers when choosing their model; full-history forks inherit the parent in runtimes that reject overrides. Other native roles inherit the parent unless the user chooses an available model. Preserve explicit model caps. Cloud model or effort control must be demonstrated by that backend; generic local `-c` overrides and Cursor role lines do not establish it. Report requested and confirmed settings separately. Different OpenAI models do not constitute cross-family review.

Translate user-input and planning tools to the actual host. Use the installed skill-creator for skill authoring. Cursor Custom Modes, `/loop`, cloud automations, video services, Project stores, and event subscriptions are not supplied by these files. Report an unavailable surface rather than inventing it or starting a paid service to emulate it.

## Coordinate durable runs

For cloud or mixed plans, use the [run-state contract](../../swarm/references/run-state.md). Keep the stable effort under `.pstack/runs/<run-id>/`, with registry, briefs, retrieved results, evidence, and the existing TSV decision trail. Check the plan fingerprint, repository, base commits, worker IDs, ownership, and acceptance evidence before continuing. A cloud task marked completed is not accepted or integrated work. A remote pathname alone is not retrieved evidence.

`$swarm-check` refreshes observations through the desktop tools and prints every planned item, parallel group, running worker, pending dependency, result, and next action. It never submits work or clears an explicit pause. A local coordinator schedules only while its session is active. Desktop-tool waits are not a persistent scheduler. Submitted cloud tasks may keep working after the coordinator stops.

A specific run resumes through [Session pickup](../playbooks/session-pickup.md): check first, then explicitly resume under the existing authorization. [Pause safely](../playbooks/pause-safely.md) stops new submissions and persists the pause; do not claim running cloud tasks were cancelled unless cancellation is actually supported and confirmed. Unknown submission outcomes require reconciliation before retrying. Preserve explicit pauses across new sessions, status checks, and restarts.

Integrate retrieved patches in isolated local worktrees and recheck the affected artifact. The coordinator owns local integration and forge operations unless the cloud environment's permissions and workflow were independently established. Author and verifier must be independent, their results tied to exact commits. A new base or changed patch requires the applicable fresh checks. Helpers do not apply patches, commit, merge, publish, or grant authority for those actions.

## Verification and authority

Generate and discover project verification skills under `.agents/skills/verify-<app>/`. Both Codex and Cursor can read that location. Existing `.cursor/skills` verifiers can be read explicitly; do not silently duplicate or move them. Cloud briefs must make their verifier available remotely before asking a worker to use it. Preserve every required scenario but batch lanes within the configured limit. No unavailable live surface or missing evidence counts as a pass.

An invoked skill guides the current task; installation is not a Git hook or a persistent mode across conversations. It creates no agents, cloud capacity, recurring service, or additional authority to publish, merge, message, or deploy. Follow the user's grants and gates over upstream autonomy prose. Resolve skill source locations from this installation, not an assumed `pstack/skills` directory inside every product repository.
