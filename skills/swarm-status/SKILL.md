---
name: swarm-status
description: Scan a project's saved Cloud and native swarm runs and write a concise SWARM-STATUS.md with completion, worker IDs, blockers, evidence links, and resume prompts.
---

# Swarm status

Use this for a project-wide overview. Resolve the named project or use the current project directory. Inspect that project's .pstack/runs/*/state.json registries.

Run the bundled scanner with the project path and the timezone from the current user context:

~~~sh
python3 <this-skill>/scripts/scan.py --project <project-directory> --timezone <user-timezone>
~~~

It writes SWARM-STATUS.md in that project, reusing the shared registry reader for Cloud, native, and mixed runs. The report includes run IDs, worker IDs, accepted counts, scheduling, observations, blockers, evidence links, and continuation prompts. Malformed runs appear as inspection errors while other runs remain visible.

Default to saved observations. For a requested live refresh, first use [swarm-check](../swarm-check/SKILL.md) for Cloud workers and actual native collaboration tools for reachable subagents, then regenerate the Markdown. Scanning preserves scheduling and worker state. Continuation requires a separate user request.

Use swarm-cloud prompts for Cloud or mixed runs and swarm-sub prompts for native-only runs. Reconcile uncertain submissions before scheduling. A completed run remains complete after its coordinator lease expires. Last-observed time alone cannot establish a stuck worker.

Native sessions appear when their workers were recorded in the [run registry](../swarm/references/run-state.md). Historical native sessions without a registry require the original conversation.

Return the report link and a short count of complete and unfinished runs. Mention inspection errors or missing native history when relevant.
