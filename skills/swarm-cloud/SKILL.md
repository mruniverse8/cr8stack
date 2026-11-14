---
name: swarm-cloud
description: Run parallel Codex Cloud workers through desktop tools, select an environment or use Default, and save dependencies and results for recovery.
---

# Swarm Cloud

Use the loaded Codex desktop tools for Cloud execution. Read the [desktop workflow](references/desktop-cloud.md), [worker contract](../swarm/references/worker-contract.md), and [run registry](../swarm/references/run-state.md). The desktop session coordinates independent Cloud workspaces. Scheduling advances while a coordinator is active.

## Frame and select

State the goal, work items, dependencies, acceptance checks, and parallel limit. Reuse a saved run when continuing its plan. Repository-free tasks need a self-contained brief. Repository tasks also need accessible source, a starting commit, and bounded output ownership.

Discover list_cloud_environments and create_thread through the host's loaded tools. Follow environment pagination through its final page. Resolve a user-named environment by its returned configuration ID or unambiguous name. If none was requested, use the discovered runnable **Default environment**. Save its environmentConfigId in the run. An explicitly requested unavailable environment needs resolution from the user. If Default is unavailable, report the actual setup gap and direct the user to Cloud environment setup.

## Launch

Initialize the local registry, configure the discovered environment, and acquire the coordinator lease. The helper's prepare command checks dependencies and capacity, saves a submission token, and returns the create_thread arguments. Invoke that loaded tool with target.type set to codexCloud and the selected configuration ID. Immediately save and bind its response. Follow the [desktop workflow](references/desktop-cloud.md) for pending setup and uncertain submissions.

Create one task per work item within the declared limit. Leave the model at the user's configured default unless the user explicitly requests one. Requested model and effort settings must be supported by the actual tool. Arena candidate and judge passes retain their separate [cost approvals](../arena/references/cost-approval.md).

## Collect and verify

Use wait_threads for progress and read_thread for each worker's current turn and command outputs. Save the raw response, import it with observe, and retrieve the actual artifacts. Inspect returned source or patches before independent execution or integration. Preserve exact contents and check hashes for text artifacts. For repository changes, verify the actual starting commit and integrated revision.

A completed turn awaits independent acceptance. Record a receipt tied to the retrieved result and local evidence after checks pass. Dependencies become ready when their required results are accepted and their source or artifact inputs are available to the next worker.

## Recover and report

Use [swarm-check](../swarm-check/SKILL.md) for observation and [Session pickup](../poteto-mode/playbooks/session-pickup.md) for authorized continuation. Preserve scheduling pauses while recording late responses and results. Keep threadId, hostId, and pending clientThreadId distinct.

Report all planned work, environment, worker titles and IDs, dependencies, observations, retrieved artifacts, verification status, and next actions. Attribute launches to the desktop connector. Tool calls execute in the active Codex session. The local Python helper persists coordination and prepares requests.
