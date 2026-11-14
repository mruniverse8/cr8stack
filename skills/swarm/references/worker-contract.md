# Worker contract

Each assignment names its backend, goal, bounded ownership, dependencies, source identity where applicable, output, acceptance checks, and authorized external actions. Default parallel Codex work uses desktop Cloud. Explicit native work uses swarm-sub. For races, declare first pass, rank all, or best-of before launching.

Cloud briefs contain the required instructions and accessible inputs. Local absolute paths and unpushed changes require an actual transfer before remote use. Repository tasks identify the intended revision and record the actual starting commit. Repository-free tasks record source commit as N/A and identify returned artifacts by hashes.

Workers return PASS, ISSUES, or BLOCKED with changed paths, commands, exit codes, exact output, findings, and missing evidence. For small text artifacts, return complete contents and SHA-256 values. For repository edits, return an accessible patch with its identity. Measurements also name sample count, order, method, and baseline/head revisions.

The coordinator saves desktop creation responses and read_thread results, retrieves claimed artifacts, inspects their contents, and independently verifies them. A remote pathname or worker self-report requires further retrieval and checking. Keep credentials out of prompts and evidence.

A completed worker awaits acceptance against the actual artifact. Match source hashes, execution records, and the revision being integrated. Store local verification outputs and a receipt covering every acceptance criterion. Recheck affected evidence when artifacts or source identities change. Make accepted dependency data available to subsequent workers.

For missing evidence, make one bounded request through an available follow-up mechanism under the task authorization, then report remaining coverage gaps. Reconcile uncertain creations against their submission tokens before replacement work. Preserve scheduling pauses and worker identities across sessions. The registry supports recovery while the coordinator owns interpretation, integration, and authorized external actions.
