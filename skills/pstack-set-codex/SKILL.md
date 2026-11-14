---
name: pstack-set-codex
description: >-
  Configure pstack roles against the Codex models available now. Use for
  /pstack-set-codex, Codex model setup for pstack, gpt-6-sol, gpt-6.1-terra,
  gpt-6-astra, or before arena and why.
disable-model-invocation: true
---

# Set Codex models for pstack

The role table is [models.md](references/models.md). Read it before writing the rule, and before arena or why.

## Steps

### 1. Check the catalog

Run `command -v codex`. Run `codex debug models`. Keep slugs whose `visibility` is `list`.

The required slugs are `gpt-6-sol`, `gpt-6.1-terra`, and `gpt-6-astra`. Stop when one is missing and name it.

### 2. Show the table

Show the role lines from models.md. Astra fills hardest tasks, the arena judge, and the second interrogate seat. Validation stays on Cursor cloud with `grok-4.7-xhigh-fast`.

### 3. Write the rule

Write `~/.cursor/rules/pstack-codex.mdc` with `alwaysApply: true`. Overwrite that file. Copy the role lines from models.md. Leave `~/.cursor/rules/pstack-models.mdc` as the Cursor Task table from `/setup-pstack`.

### 4. Confirm

Say the Codex rule applies on the next session. Repeat the arena and why permission note from models.md. Do not start either pass during setup.
