---
name: principle-laziness-protocol
description: "Apply when refactoring, evaluating diff size, or tempted to add abstractions, layers, or signal threading. Bias toward deletion and the smallest change that solves the problem."
disable-model-invocation: true
---

> **Codex only:** Read [the local runtime adapter](../poteto-mode/references/local-codex-compatibility.md) before following this Cursor-authored workflow. Cursor follows the instructions below unchanged.


# Laziness Protocol

- **Consolidate decisions.** Do not repeat the same choice in several places. Put it behind one source of truth and pass the result as a simple flag.
- **Minimize the diff.** Make the smallest change that solves the problem. Fewer lines beat "elegant" boilerplate.
