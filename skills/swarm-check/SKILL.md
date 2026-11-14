---
name: swarm-check
description: Refresh saved desktop Cloud workers and report paused scheduling, dependencies, parallel work, results, and verification gaps.
---

# Swarm check

For a concise Markdown overview of all saved runs in a project, use [swarm-status](../swarm-status/SKILL.md). This skill refreshes the selected run.

Find the user-named run or the current project's saved run under .pstack/runs/. Resolve ambiguity within that project. Read [run state](../swarm/references/run-state.md).

Run the local helper's check command with --run <directory> --json to obtain saved identities and refresh requests. Invoke the loaded read_thread tool for each known Cloud thread and host. Save complete responses and import each with observe. Read further pages or outputs when needed. Import tool errors as unknown observations while retaining worker identities. Resolve pending client identities through the [desktop workflow](../swarm-cloud/references/desktop-cloud.md).

Run check again to print the combined report. Identify which observations were refreshed and which remain saved or inaccessible. For an offline request, use check --offline and label the observations stale. Live refresh occurs through loaded desktop tools.

Print scheduling state, pause reason, last refresh, planned parallel groups, active or uncertain workers, and ready-but-unscheduled work. Include each task's environment, backend, dependencies, title, thread and host IDs, results, evidence, acceptance status, and next action. Treat worker assertions as unverified input.

Preserve pauses during checking. For authorized continuation, use [Session pickup](../poteto-mode/playbooks/session-pickup.md). For requested continuous monitoring, use bounded wait_threads calls followed by read_thread and observe while the coordinator is active.
