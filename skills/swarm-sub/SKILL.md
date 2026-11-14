---
name: swarm-sub
description: Delegate parallel work to native Codex subagents in the current execution environment, with explicit models and bounded evidence checks.
---

# Swarm subagents

Use this backend for local files, native agent messaging, local tools, and shared-host work. It creates agent threads, not separate Codex Cloud workspaces. Use [swarm-cloud](../swarm-cloud/SKILL.md) for the default Cloud execution path. Keep concurrent writes isolated by ownership or worktrees.

## Native Codex workflow

This section governs Codex swarm workers, including when `poteto-mode` calls swarm-sub. It overrides Cursor model rules, parent-model inheritance defaults, and the Cursor Task syntax below. Keep the coordinator on its current model. Use native collaboration tools; this skill does not provision cloud machines.

Track four phases: Frame, Fan out, Aggregate, Report.

### Frame

State the completion condition, required evidence, and returned artifact. Choose coverage slices, identical-brief races, or a mixture. Before a race, declare `first pass`, `rank all`, or `best-of`.

Resolve each worker's model and reasoning independently: explicit per-worker choice wins over an explicit run-wide choice, which wins over this routing table. A model override alone keeps medium reasoning; an effort override alone keeps task-based model routing. Honor caps such as "Terra only" and "do not escalate".

| Task | Model | Reasoning |
| --- | --- | --- |
| Searches, extraction, summaries, mechanical edits | `gpt-6-luna` | `medium` |
| Visual inspection, concise writing, bounded UI or code fixes | `gpt-6.1-terra` | `medium` |
| Architecture, ambiguous debugging, concurrency, integration analysis | `gpt-6.1-sol` | `medium` |
| One escalation from a substantively blocked Luna or Terra task | `gpt-6.1-sol` | `high` |

Split mixed work into bounded slices when practical. Classify a slice by its hardest required judgment, not its length; a mechanical edit with an unsettled API contract needs that contract resolved first. A scoped visual task goes to Terra; a simple textual inventory goes to Luna. User-specified race arms take precedence over routing.

Check the selected model and effort against the runtime's available choices. Authentication, quota, unsupported effort, unavailable models, missing tools, and exhausted slots are environment blockers, not evidence that a stronger model is needed. Queue for occupied slots; report other blockers. Never silently substitute the parent model or select Astra as an automatic fallback. An explicit user request for another available model remains valid.

Before spawning, announce a compact assignment table: worker, task, model, effort, and selection reason. Each brief stands alone and includes the goal, necessary context or absolute file pointers, permitted and forbidden paths, dependencies, acceptance checks, and expected report. Include exact SHAs for commit verification and the sampling method for measurements. Give concurrent writers distinct ownership or isolated worktrees; local agents share the filesystem.

### Fan out

Use `collaboration.spawn_agent` with explicit `task_name`, `message`, `model`, `reasoning_effort`, and `fork_turns: "none"`. In this runtime, full-history forks inherit the parent model and do not accept model or effort overrides. Supply the required context in the brief instead. Do not pass Cursor-only `subagent_type`, `environment`, `run_in_background`, or `cloud_base_branch` arguments.

For example, a routine worker uses this argument shape (through the tool, not a shell command):

```json
{
  "task_name": "inventory",
  "message": "<self-contained task brief with scope and acceptance checks>",
  "fork_turns": "none",
  "model": "gpt-6-luna",
  "reasoning_effort": "medium"
}
```

Launch independent workers within available capacity and queue excess slices. Use `collaboration.list_agents` for status, `collaboration.wait_agent` for completion notifications, and messaging or interruption tools for corrections. If the host exposes equivalent native tools under different names, follow its actual schema. If explicit model selection is unsupported, report that gap rather than claiming the requested model ran.

Before spawning, initialize every native swarm under the current project's .pstack/runs/<run-name>/ using the shared [run registry](../swarm/references/run-state.md), including native-only runs. Define tasks with backend sub and record returned native IDs with record-sub immediately after spawning. Record final observations and save each report as results/<item>/native-result.md, starting with PASS, ISSUES, or BLOCKED and its reason. Retain verification evidence before acceptance. This makes native runs discoverable by [swarm-status](../swarm-status/SKILL.md) after the current session. Reconcile an unreachable prior worker before assigning its unfinished scope to a fresh worker.

Workers return `PASS`, `ISSUES`, or `BLOCKED` with evidence. A completed review that proves defects is `ISSUES`, not a failed task. Account for dropouts and missing slices; they cannot count as passes.

### Aggregate and escalate

Inspect actual findings, diffs, artifacts, and acceptance-check output. Require the SHAs and measurement method specified in each brief. Preserve the original bounded evidence retry: if required evidence is missing, discard the unsupported verdict and request one fresh attempt on the same model and effort. A second miss becomes a coverage gap, not another retry or automatic escalation.

Unless the user forbids escalation or caps models, a Luna or Terra task blocked by substantive reasoning or implementation difficulty may receive one fresh Sol attempt at high reasoning. An explicit reasoning constraint still wins. Pass Sol the original brief, attempted work, failure evidence, remaining acceptance checks, and ownership of any existing changes. Stop the earlier writer before transferring ownership. Record that escalation was used; never escalate the same task again, including after an evidence retry. Already-Sol workers and environment blockers do not trigger model escalation.

Apply the declared race rule. Evidence retries retain the arm's model. An authorized Sol escalation is a rescue attempt outside the original model comparison: report it separately and do not credit its result to the original arm.

### Report

Return one consolidated report with each task's requested/accepted model and effort, outcome, evidence, escalations, and gaps. Include the runtime-reported actual model only when available; do not infer it from a worker's self-description. Include proven issue summaries and the race rule when used. Keep the coordinator responsible for final verification.

Example request: `$swarm Review this change. Choose worker models by task difficulty. Use Terra for the UI review and Sol for concurrency analysis.`

Read the shared [worker contract](../swarm/references/worker-contract.md). Record native IDs and observations through `record-sub` in the [run registry](../swarm/references/run-state.md). An old native thread may no longer be reachable after a host restart; report that fact and retain its evidence rather than presenting it as a live cloud task.
