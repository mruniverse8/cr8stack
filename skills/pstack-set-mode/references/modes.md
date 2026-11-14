# Host mode

Two hosts. The process you are in picks the host. Cloud is a place either host can run, and it does not change the host.

## Detect

This process is Cursor when any of these hold:

- The session is a Cursor cloud agent. Its page is `https://cursor.com/agents/<bcId>`. The VM being in the cloud does not make the session Codex.
- The session is the Cursor IDE or a Cursor desktop agent.
- The Task tool can spawn a subagent.

This process is Codex only when the session itself is Codex and the tests above are false.

Do not run `command -v codex` to decide. A missing `codex` binary does not block Cursor cloud work. A present `codex` binary does not make a Cursor session into Codex.

The process wins. A saved line that names the other host is stale. Ignore it.

## cursor

Roles come from `~/.cursor/rules/pstack-models.mdc`. When that file is missing, use the `/setup-pstack` defaults.

Cloud workers are Cursor cloud agents. Spawn them with the Task tool and `environment: "cloud"`. Use `machine.type: new_cloud_vm` when a worker needs its own VM and branch. They show up at `https://cursor.com/agents`. `$swarm-cloud` means this path.

Do not read the Codex model table. Do not run `codex cloud exec`. Do not describe the workers as ChatGPT tasks.

Arena and why use the Cursor role lines. They do not ask the Codex cost gate.

## codex

Roles come from [models.md](../../pstack-set-codex/references/models.md).

`$swarm-sub` uses native Codex workers. `$swarm-cloud` uses `codex cloud exec`. Those tasks show up in ChatGPT.

Arena and why ask permission before the parallel panel. A missing yes stops that pass.

## Record

On Cursor, write `~/.cursor/rules/pstack-mode.mdc` with `alwaysApply: true` and the line `mode: cursor`. When this repo is the skill pack, write the same fact to `.cursor/rules/pstack-mode.mdc` so the next cloud agent on the repo sees it.

Delete `~/.cursor/rules/pstack-codex.mdc` when it exists. That file is an always-applied Codex table inside Cursor.

On Codex, write `~/.codex/pstack-mode.md` with the line `mode: codex`. Do not write a Cursor always-apply rule.
