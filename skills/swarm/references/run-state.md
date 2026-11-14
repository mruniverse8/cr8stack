# Durable runs

A saved run is a dependency graph for one unchanged plan. It outlives a conversation. Coordinator identities are unique per session; choose a fresh UUID. Keep `.pstack/runs/<run-name>/` in the project, excluded from Git using the project's existing ignore mechanism. Do not change tracked ignore rules or commit run data just to pause. This local directory supports recovery on the same machine; transferring a run to another machine requires a secure copy of its state and evidence, path rebasing, and renewed validation. It is not a distributed lock or a hosted scheduler.

## Storage

`state.json` holds version 1, a stable run ID, repository, Cloud environment, maximum parallel workers, plan path/hash, immutable task definitions, provider IDs and observations, submission tokens, patches, acceptance receipts, scheduling state, and a coordinator lease. `plan.md` is the original plan snapshot. `briefs/` preserves dispatched instructions. `results/` holds content-addressed raw patches and extracted reports, retaining historical versions when a provider revises its output, plus the latest status snapshot. `evidence/` can hold verification outputs. `decisions.tsv` is the append-only [show-me-your-work](../../show-me-your-work/SKILL.md) log. Keep authorization, permitted actions, and review gates in the fingerprinted plan, not an invented permission flag.

State writes are atomic and commands hold a nonblocking file lock. The coordinator lease lasts five minutes and is renewed by owner actions. A missing/expired lease means orphaned coordination, not failed workers. Another owner cannot resume an unexpired lease. `check` does not acquire or renew ownership; a running watch never claims to be a scheduler. A lease expiring permits recovery only under the original user authorization. An explicit pause remains until the user requests resume. There is no background daemon to install.

Task fields are `id`, `title`, `backend` (`cloud` or `sub`), `depends_on` (IDs), `branch` (on origin), `brief`, `acceptance` (criterion strings), and `allowed_paths`. IDs are unique path-safe names and dependencies must form a DAG. The helper fingerprints these definitions and the plan. A changed definition requires a revised run. A changed or missing external plan holds execution and acceptance but still allows check, retrieval, offline reporting, and pause, so workers remain recoverable. Reassess receipts explicitly in a revised run instead of automatically reusing them. Example spec:

```json
{"tasks":[{"id":"auth","title":"Authentication fix","backend":"cloud","depends_on":[],"branch":"feature/auth","brief":"Fix the agreed authentication defect.","acceptance":["original reproduction passes"],"allowed_paths":["src/auth/","tests/auth/"]}]}
```

## Commands

Invoke with `python3 <skills>/swarm-cloud/scripts/cloud_tasks.py` followed by one of these subcommands. Paths in arguments are local. No command applies patches, commits, pushes, opens PRs, merges, or executes commands embedded in results.

| Command | Arguments and effect |
| --- | --- |
| `init` | `--run DIR --plan FILE --spec JSON --repo DIR --env ID --max-parallel 2`. Creates state without submitting. |
| `check` | `--run DIR [--offline] [--json]`. Refreshes known Cloud IDs, retrieves available patches/reports, prints all items and dependency waves. Offline prints saved observations only. |
| `resume` | `--run DIR --owner SESSION_UUID`. Explicitly lifts pause, checks Cloud state, acquires/renews the lease. Does not submit. Use only when the user requested continuation or recovery is already authorized. |
| `pause` | `--run DIR --reason TEXT`. Persistently stops scheduling and releases the lease. Cloud workers may continue. |
| `submit` | `--run DIR --item ID --owner SESSION_UUID`. Refreshes state, checks dependencies and parallel capacity, records intent, then submits exactly one Cloud task. |
| `bind` | `--run DIR --item ID --task-id CLOUD_ID --submission-token TOKEN --owner SESSION_UUID`. After manually verifying the task corresponds to the saved token, binds an uncertain submission. Requires the same Cloud environment and prevents duplicate ID assignment. |
| `record-sub` | `--run DIR --item ID --task-id NATIVE_ID --status running\|completed\|failed\|unknown --base-sha SHA --owner SESSION_UUID`. Records the coordinator's observation of a native worker. It cannot query native threads or revive them. |
| `accept` | `--run DIR --item ID --receipt JSON --owner SESSION_UUID`. Records independently checked evidence for the integrated commit. |
| `watch` | `--run DIR --interval 30 --iterations 10 [--json]`. Finite check-only loop; Ctrl-C stops the local watch, not Cloud workers. |

Use a concurrency limit appropriate for the account. Pending, unknown, and uncertain submissions occupy capacity. The helper cannot enumerate native runtime slots or Cloud subscription limits. Record native observations truthfully and honor both runtime and run-wide limits.

## Recovery

Start Session pickup with a run directory. Check first. Reconcile unknown submissions before retrying. The helper persists intent before sending a request, so a timeout or crash can leave `submission_unknown`; its token and brief must be matched to the actual Cloud task in the available UI/CLI before bind. A missing task in list is unknown, even after a successful list request. A provider outage never turns workers into failed tasks.

Read the refreshed table. Retain explicit pauses unless the user requested resume. If the prior coordinator disappeared and continuation is authorized, resume with a new session UUID after the old lease expires. Do not steal an unexpired lease. Verify retrieved results and integrate accepted changes, then submit only the ready frontier. Dependents require accepted receipts and ancestry of integration commits on their submitted branch. No automatic submission happens in check/resume/watch.

## Acceptance

Retrieve first. Inspect patches in an isolated worktree and inspect the actual worker source SHA. A branch name alone cannot establish the tested source. Run acceptance commands independently on the integrated artifact, retain nonempty outputs, and create a receipt with `task_id`, actual `base_sha`, `patch_sha256` for Cloud, `verified_sha`, `integrated_sha`, `evidence` (absolute file paths), and `checks` (objects with `criterion`, `command`, `exit_code`, `output`). Every criterion needs a passing check. Verified and integrated full commit SHAs must agree and be in the local checkout's history; the source base must be their ancestor.

The helper hashes evidence/output files and the retrieved patch. A missing or changed file, changed source identity, changed patch, or unfinished worker invalidates acceptance. It validates receipts structurally; it does not prove a command was run or that its assertions are meaningful. The coordinator inspects evidence and owns those judgments. Never manufacture a receipt from worker assertions. Report-only tasks can use the unchanged verified source commit as their integration commit after their result has been independently checked. Store their evidence off the product branch.

## Output

Report scheduling as paused, active, or orphaned, with reason and last check. Print topological planned parallel groups, active/uncertain IDs, and ready-but-unscheduled IDs. Every item shows title, backend, dependencies, provider/native ID, worker observation, retrieved result, verification/integration state, and next action. Label extracted worker reports unverified. A provider pending status cannot distinguish queueing from running. Unknown observations and retrieval errors stay visible. Status checks never become behavioral verdicts.
