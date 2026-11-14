# Codex Cloud through desktop tools

Follow the [desktop workflow](../../swarm-cloud/references/desktop-cloud.md) for discovery, environment selection, worker creation, retrieval, and recovery.

The loaded list_cloud_environments tool returns saved configuration IDs. create_thread with target.type set to codexCloud creates a worker and returns its identity. wait_threads and read_thread observe and retrieve that worker. Explicit native work uses [swarm-sub](../../swarm-sub/SKILL.md).

The [local helper](../../swarm-cloud/scripts/cloud_tasks.py) persists runs and prepares requests. Version 1 records remain available for inspection and pause while their worker identities are reconciled.

Official setup guidance is available in [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments). Check the current loaded schemas for host capabilities.
