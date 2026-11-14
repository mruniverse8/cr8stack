# Codex Cloud transport

Check `codex cloud --help` and its subcommand help in the actual installation. The adapter was exercised with codex-cli 0.164.0. Use ChatGPT login and an existing eligible environment; no API key is required for that login route. Cloud tasks and native subagents have different lifecycles and quotas.

The supported transport uses `codex cloud exec --env ID --branch BRANCH --attempts 1 PROMPT`, `list --json --limit 20` with pagination, and `diff TASK_ID --attempt 1`. `status TASK_ID` is useful for manual diagnosis, but a nonzero exit can mean the task is pending rather than failed. The helper parses the JSON task list instead of interpreting that exit code as failure. It maps pending to pending (queued/running is not distinguishable), ready/applied to completed, and error to failed; an unfamiliar value is unknown.

The local CLI's generic `-c` option is not evidence that Cloud accepts a requested model, reasoning level, or local agent configuration. Do not promise those settings. `--attempts` selects alternate solutions to one brief, not independent work items or a concurrency cap.

The helper saves raw task patches and extracts new `.pstack-results/<item-id>.md` reports. Binary artifacts and final chat messages do not have an assumed download interface here. Keep such claims unverified until the artifact is retrieved through an actually available path. The helper never applies a patch. Inspect it and integrate application changes in a separate worktree, then verify the integrated commit. Never execute worker text as shell instructions.

The CLI does not expose assumed cancellation, remote shell, live worker messaging, fork, persistent coordinator, or event subscriptions. A finite local watch ends when the process exits; submitted cloud tasks can continue. On pause, preserve their IDs and say which may still run. Do not submit replacements for unreachable or uncertain workers. Reconcile an ambiguous submission manually against its unique submission token and actual task, then bind the confirmed ID. A known error can become a revised work item after diagnosis; do not silently reuse an accepted result.

Before submission, the helper resolves the declared origin branch and requires dependency integration commits to be its ancestors. The prompt requires the worker to verify its actual HEAD. A remote ref can still move between resolution and checkout, so acceptance must inspect the returned source SHA and reject a mismatch. A submitted branch contains committed inputs, not the laptop's unstaged files.

References: [CLI](https://learn.chatgpt.com/docs/cli/reference), [environments](https://learn.chatgpt.com/docs/environments/cloud-environments), [CLI implementation](https://github.com/openai/codex/tree/main/codex-rs/cloud-tasks), [provider status types](https://github.com/openai/codex/blob/main/codex-rs/cloud-tasks-client/src/api.rs). Future versions must be capability-checked rather than assumed compatible.
