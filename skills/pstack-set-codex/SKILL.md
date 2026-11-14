---
name: pstack-set-codex
description: >-
  Configure pstack roles against the Codex models available now. Use for
  /pstack-set-codex, Codex model setup for pstack, gpt-6-sol, gpt-6.1-terra,
  gpt-6-astra, or before arena and why.
disable-model-invocation: true
---

# Set Codex models for pstack

The role table is [models.md](references/models.md). Read [modes](../pstack-set-mode/references/modes.md) first. This skill sets Codex models. It does not set the host.

## Steps

### 1. Stay on the Codex host

When this process is Cursor, including a Cursor cloud agent, stop. Codex model setup runs in a Codex session. Do not write `~/.cursor/rules/pstack-codex.mdc`. If that file exists, delete it.

### 2. Check the catalog

Run `command -v codex`. Run `codex debug models`. Keep slugs whose `visibility` is `list`.

The required slugs are `gpt-6-sol`, `gpt-6.1-terra`, and `gpt-6-astra`. Stop when one is missing and name it.

### 3. Show the table

Show the role lines from models.md. Astra fills hardest tasks, the arena judge, and the second interrogate seat. Validation stays on Cursor cloud with `grok-4.7-xhigh-fast`.

### 4. Leave the Cursor rule alone

Do not write `~/.cursor/rules/pstack-codex.mdc`. The role lines stay in models.md and apply when mode is codex. Leave `~/.cursor/rules/pstack-models.mdc` as the Cursor Task table from `/setup-pstack`.

### 5. Confirm

Say the Codex table applies in Codex sessions. Repeat the arena and why permission note from models.md. Do not start either pass during setup.
