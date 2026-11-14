---
name: swarm
description: "Fan out N parallel workers, drain them, and return one report. Use for /swarm, 'swarm this', or parallel coverage, races, gauntlets, and exploration."
disable-model-invocation: true
---

> **Codex:** Read [the local runtime adapter](../poteto-mode/references/local-codex-compatibility.md), then use the Codex workflow below. **Cursor:** skip the Codex workflow and use the original workflow under Start.


# Swarm

## Codex execution routing

Choose a backend before delegating. `$swarm-sub` or an explicit subagent request uses [swarm-sub](../swarm-sub/SKILL.md). `$swarm-cloud` or an explicit Codex Cloud request uses [swarm-cloud](../swarm-cloud/SKILL.md). An unspecified `$swarm` keeps the native subagent default. A plan may select different backends for separate work items; name the backend in the assignment table. Never silently switch after a backend fails.

Both backends use Frame, Fan out, Aggregate, Report. State the completion condition, coverage slices, required evidence, and returned artifact. Before a race choose first pass, rank all, or best-of. Read the [worker contract](references/worker-contract.md). The backend owns model selection, launch, capacity, result retrieval, and retries. The coordinator inspects the real output and returns PASS, ISSUES, or BLOCKED for each slice; missing evidence is a gap.

For durable plans read [run state](references/run-state.md). `$swarm-check` reconciles observations and prints every planned work item without submitting jobs. To continue a particular run, use poteto-mode's Session pickup playbook. A status check never lifts an explicit pause or implies acceptance.

Cursor uses the original workflow below. Codex uses the selected backend and stops here.

## Start

Open a todolist with one entry per phase before launching anything.

1. Frame
2. Fan out
3. Aggregate
4. Report

## Phase A: Frame

1. State the done predicate and the artifact or report the swarm must return.
2. Choose the shape. Partition into slices, race N workers on identical briefs, or mix both. For a race or mixed shape, declare `first pass`, `rank all`, or `best-of` before spawning.
3. Pick the worker model from the `swarm workers` line in `~/.cursor/rules/pstack-models.mdc`. If the rule or that line is missing, use `grok-4.7-xhigh-fast`. For `auto` or `inherit-parent`, omit `model` so the workers run on the parent model. If the Task tool rejects a slug, use the default and say so. If it rejects the default, use the closest valid slug of the same family from its error message. For a model race, name each arm's model up front. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section of the **poteto-mode** skill.
4. Give each worker its own writable output when it writes. When workers verify or measure commits, each brief names the exact SHAs. A measurement brief also names the method (sample count, what one sample is, order). The worker records both in its result.

## Phase B: Fan out

Spawn all N workers in one message with `subagent_type: generalPurpose`, `environment: "cloud"`, `run_in_background: true`, and the step 3 model, left unset for `auto` or `inherit-parent`. Use `environment: "local"` only when the worker needs access to something on the user's computer.

When a worker must start from a non-default pushed branch, pass `cloud_base_branch`.

Every brief stands alone. Include the goal, scope, exact slice or race arm, how to verify, and what to report. Reports use `PASS`, `ISSUES`, or `BLOCKED` with evidence. A worker that can prove a defect reports `ISSUES` and lists every issue it can prove, not only the first.

If a worker drops out, proceed with N-1 and note it.

## Phase C: Aggregate

Read the terminal results. Drop a result that does not record the SHAs and method its brief names, and respawn that worker once. After a second miss, record a gap. A gap does not count as a pass. For coverage, every required slice needs a result. For a race, apply the selection rule declared up front. Use first pass, rank all, or best-of. Do not paste raw worker dumps.

## Phase D: Report

Return one consolidated in-chat report with a result table, issue one-liners, gaps or dropouts, and the race rule when used.
