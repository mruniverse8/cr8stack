# cr8stack for Codex

The codex branch contains the Codex adaptation of the pstack skills in skills/. It includes desktop Cloud workers, native subagents, durable run recovery, and a project-wide swarm status report.

## Install

Clone this branch and copy the skills into your personal Codex skills directory.

```sh
git clone --branch codex https://github.com/mruniverse8/cr8stack.git
cd cr8stack
mkdir -p ~/.codex/skills
cp -R skills/. ~/.codex/skills/
```

The skills become available in a new Codex conversation. The agents-skills/ directory contains the separate workflow collection already bundled in this repository.

## Use

- Invoke $poteto-mode with a task to select a workflow.
- Invoke $swarm-cloud for parallel Cloud tasks through the loaded Codex desktop tools. With no requested environment, it selects the discovered runnable Default environment.
- Invoke $swarm-sub for native subagents in the current execution environment.
- Invoke $swarm-check to refresh a selected saved run.
- Invoke $swarm-status to write SWARM-STATUS.md for the current project's saved Cloud and native runs.

For example, send this in Codex desktop.

```text
$swarm-cloud Build a small Tetris game in ./tetris-simple/ and verify it on localhost.
```

Cloud execution requires the desktop tools and an accessible runnable environment. Native-only work uses the native collaboration tools. Arena candidate and judge passes require scoped approval.

## Recovery

Runs are saved separately under each project's .pstack/runs/<run-name>/. Keep the full run directory and its evidence when moving between machines. Cloud threads and native workers retain their recorded identities.

```text
$swarm-status
```

The generated report includes IDs, completion, blockers, evidence links, and continuation prompts. A Cloud continuation request can name the saved directory directly.

```text
$swarm-cloud Resume the existing run at /path/to/project/.pstack/runs/my-run.
```

The coordinator refreshes existing workers and reconciles uncertain submissions before continuing. Dependency scheduling requires an active coordinator session.

## Checks

```sh
python3 -m unittest discover -s skills/swarm-cloud/tests -v
python3 skills/swarm-status/scripts/scan.py --project /path/to/project
```

The optional smoke-transcript check runs when local Cloud test evidence is present. Runtime registries, screenshots, local installation receipts, and interpreter caches are excluded from this repository.

The Codex runtime adapter takes precedence over Cursor-specific instructions in the preserved upstream skill bodies. See skills/poteto-mode/references/local-codex-compatibility.md for the execution rules.
