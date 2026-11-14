---
name: pstack-set-mode
description: >-
  Set whether this pstack process is Cursor or Codex. Use for /pstack-set-mode,
  host mode, Cursor cloud agents, swarm-cloud on Cursor, or when a cloud agent
  starts looking for the Codex CLI. A Cursor cloud agent stays on Cursor.
disable-model-invocation: true
---

# Set the pstack host

The host table is [modes.md](references/modes.md). Read it before choosing a backend, and before arena, why, or swarm-cloud.

This process is the host. A cloud VM does not switch it. Cursor cloud agents are Cursor. Codex cloud tasks are Codex.

## Steps

### 1. Detect

Apply the tests in modes.md. Do not run `command -v codex` as the test.

### 2. Show the host

Say which host this process is. Say what `$swarm-cloud` means on that host and where the worker shows up.

On Cursor, `$swarm-cloud` spawns Cursor cloud agents at `https://cursor.com/agents`. On Codex, `$swarm-cloud` submits Codex Cloud tasks that show up in ChatGPT.

### 3. Record it

Follow the Record section in modes.md. Overwrite the mode file. Leave `~/.cursor/rules/pstack-models.mdc` as the Cursor Task table from `/setup-pstack`.

### 4. Confirm

Say the mode applies to this process. A request to use the other host does not change this process. Tell the user to open that host for that mode. Do not launch workers during setup.
