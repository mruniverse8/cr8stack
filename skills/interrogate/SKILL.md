---
name: interrogate
description: "Use for \"interrogate\", \"adversarial review\", \"multi-model review\", \"challenge this\", \"stress test this code\", \"find blind spots\", or \"tear this apart\". Adversaries try to break a change or design, and only findings proven by a run survive."
disable-model-invocation: true
---

> **Codex only:** Read [the local runtime adapter](../poteto-mode/references/local-codex-compatibility.md) before following this Cursor-authored workflow. Cursor follows the instructions below unchanged.


# Interrogate

## Codex execution

In Codex, the [local adapter](../poteto-mode/references/local-codex-compatibility.md) governs delegation, models, and host capabilities. Read the [worker contract](../swarm/references/worker-contract.md) and select [swarm-sub](../swarm-sub/SKILL.md) or [swarm-cloud](../swarm-cloud/SKILL.md) at each worker boundary. Keep this skill's phases and output; the backend transports its scoped workers rather than restarting this whole skill. An unspecified backend uses Cloud through the desktop tools; explicit native requests and genuinely local-only work use native subagents. Report blockers without switching backends.

Pin the base and head SHAs for every adversary. Cloud workers may write only permitted reproduction and result artifacts, not product fixes. Retrieve their commands and evidence, then independently rerun findings on the checked code before accepting them.

## Cursor workflow and shared task phases

Adversaries try to break a change or a design. A finding survives only when a run proves it. Report the findings. Do not apply fixes.

## Frame

The scope is what the user names. Otherwise it is the branch diff from its merge base with the base branch, through the working tree. State the intent with the **in-your-own-words** skill, from the user's message, the commits, and the PR description. Ask the user when the intent is unclear.

## Fan out

Run Phase A steps 3 and 4 and Phase B of the **arena** skill, with four changes. Read the `interrogate reviewers` line in place of `arena runners`. Copy the scope's uncommitted changes into each worktree. Spawn each adversary as `generalPurpose`. In place of the arena task and rationale, give each adversary the scope, the intent, and this brief:

> Break this change. Prove each finding with a run against the real code, such as a failing test, a repro script, or command output that shows the wrong behavior. For a design or plan, run a prototype or probe the current tree. Keep repros in your own worktree. Report each finding with a title, the exact command, the output it printed, and the output the intent requires. Leave out anything you did not run. That covers style, naming, structure, and risks that need a future change to matter. No findings is a valid result.

## Verify

Verify each finding per arena Phase F by rerunning its command. Keep a finding when the output shows the failure and the failure breaks the intent. Drop the rest. Merge findings that share a root cause.

Skip arena Phases C, D, and E. Adversaries find different failures, so the verdict keeps every verified finding, not one adversary's list.

## Output

- **Intent**: the restatement.
- **Findings**: for each verified finding, the command, its output, how it breaks the intent, and the adversaries that found it. Say "no verified findings" when none survive.
- **Dropped**: for each adversary, the count of dropped findings and why.
