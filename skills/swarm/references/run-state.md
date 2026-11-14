# Durable desktop Cloud runs

Save the run under .pstack/runs/<run-name>/ using the project's existing ignore mechanism. Its graph, worker identities, and evidence support recovery on this machine. Cross-machine recovery requires transferring those files, rebasing evidence paths, and checking access to the saved workers.

## Storage and definitions

Version 2 state has transport desktop-tools, stable run ID, optional local repository, immutable requested environment, selected desktop configuration, maximum parallel workers, fingerprinted plan and task definitions, scheduling state, and a five-minute coordinator lease. The environment stores environmentConfigId, name, and listed repositories.

Task fields are id, title, backend (cloud or sub), depends_on, optional branch, brief, acceptance criterion strings, and allowed_paths. IDs are path-safe and dependencies form a DAG. Branches apply to repository work. For repository-free work, omit the run repository and branch. The backend defaults to cloud.

~~~json
{"tasks":[{"id":"primes","title":"Primes from 0 through 99","brief":"Create and run primes_0_100.py for 0 <= n < 100. Return source, SHA-256, and command output.","acceptance":["output matches independent sieve"],"allowed_paths":["primes_0_100.py"]}]}
~~~

briefs/ holds prepared requests and submission tokens. results/ holds content-addressed read_thread responses and the consolidated status report. evidence/ holds retrieved artifacts and local verification output. decisions.tsv retains the [decision trail](../../show-me-your-work/SKILL.md). State writes are atomic with nonblocking local file locks.

A changed task definition requires a revised run. A changed or missing external plan holds scheduling and acceptance while observation and pause remain available. Another coordinator can acquire an expired lease under existing authorization. An explicit pause persists until the user requests continuation.

Version 1 records remain readable and pauseable. Preserve their IDs and evidence while reconciling actual desktop identities into a revised run. Prior transport IDs require independent reconciliation before desktop use.

## Local persistence commands

Invoke python3 <skills>/swarm-cloud/scripts/cloud_tasks.py with the commands below. The active Codex session invokes the desktop tools separately.

| Command | Arguments and effect |
| --- | --- |
| init | --run DIR --plan FILE --spec JSON [--repo DIR] [--env NAME_OR_ID] [--max-parallel 2]. Creates a version 2 run. |
| configure | --run DIR --environments FILE. Selects from the complete saved list_cloud_environments response. Omitted env selects discovered Default. |
| resume | --run DIR --owner UUID. Acquires or renews ownership and lifts pause under authorized continuation. |
| prepare | --run DIR --item ID --owner UUID. Checks dependencies and capacity, reserves a slot, and prints the create_thread request and submission token. |
| bind | --run DIR --item ID --submission-token TOKEN --response FILE. Records the creation response with threadId/hostId or pending clientThreadId. |
| observe | --run DIR --item ID --response FILE. Imports read_thread evidence or a tool error. |
| check | --run DIR [--offline] [--json]. Prints saved work and tool requests needed for live refresh. |
| pause | --run DIR --reason TEXT. Persists the pause and releases ownership. |
| accept | --run DIR --item ID --owner UUID --receipt FILE. Records independent evidence. |
| record-sub | --run DIR --item ID --task-id ID --status running/completed/failed/unknown [--base-sha SHA] --owner UUID. Records actual native observations in a mixed run. |

Save raw tool responses as JSON using the host's filesystem tools. The helper accepts decoded objects or a single text-JSON payload inside an MCP response. Preserve escaping and exact artifact bytes.

## Scheduling and recovery

Inspect the run, refresh known threads with read_thread, and import observations. check alone reads saved observations. resume changes coordination state. Use [swarm-check](../../swarm-check/SKILL.md) for the full live-check routine.

Before create_thread, run prepare and retain its output. A prepared item occupies capacity as submission_unknown. Pending, running, unknown, and uncertain items count toward the limit. Bind the creation response immediately. Preserve a clientThreadId until actual threadId and hostId are reconciled. Match uncertain submissions to the original prompt token before defining replacement work.

Refresh every active or uncertain known worker before preparing the next frontier. If desktop tools are unavailable, retain reservations and report the saved state plus access gap.

Record late creation responses and observations even during pause or after lease expiry. A status check preserves the pause. Under authorized continuation, refresh, resume with a fresh coordinator identity, and prepare ready items. Cloud workers may continue after a coordinator stops. New dependency scheduling requires an active coordinator.

## Acceptance

Retrieve actual artifacts and outputs, inspect their contents, match hashes and starting revisions, and run independent checks. Preserve the desktop execution record and the exact local artifact checked.

Receipts include task_id, base_sha (null for repository-free work), artifact_sha256 for Cloud, evidence (absolute nonempty file paths), and checks containing criterion, command, exit_code, and an output file path. Cover every declared criterion with passing evidence. The helper hashes those files and validates identities. The coordinator judges whether the commands prove the requirement.

Repository receipts also include matching verified_sha and integrated_sha. The full local commit must be reachable from HEAD and descend from the planned starting commit. Repository dependents require accepted integration commits in their planned base. Repository-free dependents receive accepted Cloud final-response data in their prepared prompts. Supply any further artifact content the next task requires.

Changed artifacts or evidence, failed retrieval, new worker turns, and unfinished status invalidate acceptance. Retain earlier snapshots for inspection. A completed turn awaits independent verification.

## Reporting

Print scheduling state, pause reason, timestamps, planned groups, active or uncertain workers, and ready-but-unscheduled work. Every item includes backend, title, desktop identities, dependencies, observations, evidence, acceptance status, gaps, and next action. Attribute native and Cloud workers to their actual execution backend.
