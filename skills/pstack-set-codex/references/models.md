# Codex models for pstack

`codex debug models` on 14 Nov 2026 listed `gpt-6-sol`, `gpt-6.1-terra`, and `gpt-6-astra`. Astra's catalog default is medium. This setup uses xhigh for Astra.

Sol writes code and holds a synthesis. Its effort is xhigh.

Terra reads, writes concise prose, and takes the bounded seat in a pair. Its effort is high.

Astra fills hardest tasks, the arena judge, and the second interrogate seat. Its effort is xhigh. Sol, Terra, and Astra are the GPT catalog on this machine.

## Permission

Ask before arena. Ask before why.

Say that arena costs a parallel panel. One `gpt-6-sol` runner at xhigh, one `gpt-6.1-terra` runner at high, and one `gpt-6-astra` judge at xhigh. Each runner gets its own worktree.

Say that why costs a parallel fan-out. One `gpt-6.1-terra` investigator at high for each evidence source, then one `gpt-6-sol` synthesizer at xhigh.

Wait for a yes in the user's own words. A missing yes stops that pass.

## Hosts

Validation runs on Cursor cloud. The swarm workers line stays `grok-4.7-xhigh-fast`. That slug is the Cursor validation default.

Every other parallel Codex role uses `codex exec --worktree`. The worker's directory is the new worktree. Parallel runs keep separate checkouts from the one open on this computer.

Codex cloud runs when the request names Codex cloud. Use `codex cloud exec --env <id> --branch <branch>` with a distinct branch per worker. Record the requested model. Treat the remote model as unverified until the task reports it.

## Role lines

Copy these lines into `~/.cursor/rules/pstack-codex.mdc`.

```
swarm workers: cursor-cloud grok-4.7-xhigh-fast
feature, refactoring: codex-worktree gpt-6-sol xhigh
bug-fix: codex-worktree gpt-6-sol xhigh
perf-issue: codex-worktree gpt-6-sol xhigh
hillclimb: codex-worktree gpt-6-sol xhigh
judgment and prose: codex-worktree gpt-6.1-terra high
hardest tasks: codex-worktree gpt-6-astra xhigh
how explorer: codex-worktree gpt-6.1-terra high
how explainer: codex-worktree gpt-6.1-terra high
why investigators: codex-worktree gpt-6.1-terra high
why synthesizer: codex-worktree gpt-6-sol xhigh
reflect tooling: codex-worktree gpt-6-sol xhigh
reflect judgment, divergent, synthesizer: codex-worktree gpt-6.1-terra high
arena runners: codex-worktree gpt-6-sol xhigh, codex-worktree gpt-6.1-terra high
arena cross-judge pool: codex-worktree gpt-6-astra xhigh
architect runners: codex-worktree gpt-6-sol xhigh, codex-worktree gpt-6.1-terra high
interrogate reviewers: codex-worktree gpt-6-sol xhigh, codex-worktree gpt-6-astra xhigh
```

## Launch

A writer:

```
codex exec --worktree -m gpt-6-sol -c model_reasoning_effort='"xhigh"' -C <repo> --sandbox workspace-write --approve-for-me --ephemeral --color never -o <run-dir>/<worker>.md -
```

A reader uses `--sandbox read-only` and leaves out `--approve-for-me`. Pass the brief on stdin. Match `-m` and the effort to the role line.
