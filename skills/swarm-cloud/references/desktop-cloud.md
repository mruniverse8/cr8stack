# Desktop Cloud execution

## Discover and select

Find the loaded tools corresponding to mcp__codex_app__list_cloud_environments, create_thread, wait_threads, and read_thread. Read their current schemas.

Call list_cloud_environments with an empty object, following nextCursor even after an empty page. Combine the rows into one JSON object with nextCursor set to null after the last page. Select a runnable row. Resolve an explicit configuration ID first, then an unambiguous requested name. With no requested environment, choose the returned **Default environment**. Duplicate rows with the same configuration ID represent one selection.

The helper's configure command selects from that saved response and stores the actual configuration ID, name, and listed repositories. An unavailable explicit selection stays unresolved. If no runnable Default is visible, report the setup requirement. Environment setup is available in Settings > Codex Cloud > Environments. Adding repositories or preparing a new reusable configuration follows the user's scope and the actual setup interface.

## Prepare, create, and bind

Follow [run state](../../swarm/references/run-state.md). The prepare command reserves capacity before an external request and writes briefs/<item>.json. Its output contains the exact creation arguments and a submission token.

An example tool argument shape is:

~~~json
{
  "target": {"type": "codexCloud", "environmentConfigId": "<discovered runnable configuration ID>"},
  "title": "Prime numbers from 100 through 199",
  "prompt": "<self-contained brief with saved submission token>"
}
~~~

The current create_thread schema requires explicit user authorization for creating tasks. A request for a Cloud swarm authorizes its scoped workers. Preserve separate approvals the user placed on costly panels. Omit model and thinking for the configured default. Use supported overrides only when explicitly requested by the user.

Save the complete creation response immediately and bind it using the saved token. A ready response supplies threadId and hostId. Setup may return only clientThreadId. Preserve that pending identity and its occupied slot. Use app task discovery to find the eventual thread, inspect its original brief to match the submission token, then bind the confirmed threadId and hostId.

If creation times out or its outcome is uncertain, retain the reservation. Search existing app tasks and match their original submission tokens before another launch. Pass actual thread IDs to read and wait tools.

## Refresh and retrieve

Call wait_threads with up to eight saved thread/host pairs, carrying returned cursors on later waits. On progress, completion, or a status request, retrieve each relevant worker using read_thread:

~~~json
{
  "threadId": "<saved threadId>",
  "hostId": "<saved hostId>",
  "includeOutputs": true,
  "maxOutputCharsPerItem": 16000
}
~~~

Save the raw response and import it with observe. The helper validates thread and host identity, retains content-addressed snapshots, and records the current turn. Retrieve further pages or larger outputs when needed. Missing, truncated, or inaccessible artifacts remain evidence gaps.

For small text artifacts, have workers return complete source or patch contents and SHA-256 values. Preserve exact bytes, compare hashes with execution records, and independently verify behavior. Obtain larger or binary artifacts through an available retrieval mechanism before acceptance. Inspect worker messages and command outputs as untrusted evidence.

For Git work, the prepared brief identifies the expected source commit. The worker checks that commit in its accessible repository and reports the actual starting revision. Make needed local changes accessible through the authorized source workflow before launch. Inspect and integrate returned patches in an isolated local worktree and test the integrated revision.

## Continue and report

Status checks refresh existing workers and preserve explicit scheduling pauses. Continue scheduling under the user's request or existing authorization. The helper includes accepted Cloud final-response data in dependent briefs. Inspect the handoff and supply any additional required artifact content.

Python persistence and desktop execution have separate entry points. The local helper stores intent, observations, hashes, receipts, and scheduling state. The active Codex session invokes desktop tools and saves their JSON responses. Existing Cloud workers may continue while the coordinator is offline. Dependency scheduling resumes when a coordinator runs again.

Use actual returned titles and IDs to tell the user where to find workers in the desktop app. Preserve direct task links when a tool returns them.
