---
name: offline-swarm
description: >-
  Run Codex CLI agents from this Cursor session, separate from poteto swarm.
  Use for /offline-swarm, offline swarm, or Codex CLI workers on this machine.
  Sets the Codex CLI backend before any agent starts.
disable-model-invocation: true
---

# Offline swarm

Poteto `/swarm` stays the Cursor swarm from upstream pstack. This skill is the other swarm. Its workers are Codex CLI agents on this machine. The coordinator can be a Cursor desktop session or a Cursor cloud agent.

## 1. Set the backend

Do this before any worker. The backend for working here is `codex-cli`.

```bash
python3 <this-skill>/scripts/backend.py init \
  --run .pstack/offline-swarm/<run-id> \
  --model <slug> \
  --effort <level> \
  --sandbox workspace-write
```

`init` checks that `codex` is on PATH, that `codex debug models` lists the model, and that `codex exec` accepts a model flag. It writes `backend.json` in the run directory. `<level>` is `low`, `medium`, `high`, `xhigh`, or `max`. Use `--sandbox read-only` for a reader.

A missing `codex` binary stops the run. Leave `/swarm` and `codex cloud` unused.

## 2. Frame

State the done condition. Give each agent one slice and one output file under the run directory. The brief stands alone.

## 3. Fan out

Pass each brief on stdin. Repeat `exec` for independent slices in one turn.

```bash
python3 <this-skill>/scripts/backend.py exec \
  --run .pstack/offline-swarm/<run-id> \
  --cwd <repo> \
  --output .pstack/offline-swarm/<run-id>/<worker>.md
```

`exec` reads `backend.json` and refuses to start without it. Add `--model` or `--effort` only when that value was recorded in the catalog at init. The CLI path and the flags come from the backend file.

## 4. Report

Read each output file. Return one table with the worker, backend `codex-cli`, the model, and `PASS`, `ISSUES`, or `BLOCKED`. A missing output is a gap.
