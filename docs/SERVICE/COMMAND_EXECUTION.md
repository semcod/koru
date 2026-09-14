---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "command-execution",
  "kind": "service",
  "version": 1,
  "title": "Command execution surfaces",
  "status": "implemented",
  "owner": "semcod/koru",
  "scope": "repository",
  "updated": "2026-09-14",
  "source_revision": "e7b3fa24433dcfd85261eeb570c698ab0ac904b3",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/koru/commit/e7b3fa24433dcfd85261eeb570c698ab0ac904b3"
  ]
}
---

# Command execution surfaces

<!-- docs:section summary -->
## Purpose and status

Choose an execution surface deliberately. Ordinary `koru.yaml` briefing sections do not start shell commands; queue executors and specific verification hooks do.

<!-- docs:section details -->
## Scope and behavior

| Surface | Execution behavior |
| --- | --- |
| Planfile `executor.kind: shell` + `koru --queue` | Runs the ticket handler |
| `koru work next --run-gates` | Runs automatic shell profile steps; IDE work still needs an agent |
| Ordinary `koru.yaml` `when:` sections | Included in briefs only |
| `when.before_complete_ticket.commands` | Verification hooks before completion in autonomous mode |
| `queue.post_run_verify` | Verification after completion in autonomous cycles |
| Policy `ci.command` | Invoked by `koru ci run` |

A shell ticket needs an ID, open lifecycle status, `executor.kind: shell`, an explicit handler, automatic mode, and ready queue execution state. Example handler: `koru ci run --project .`. Use the project's existing Planfile ticket allocation and lifecycle process; do not copy an occupied example ID.

`koru --queue --project .` processes one runnable ticket. Add `--loop` to continue through runnable shell tickets. These commands execute configured handlers and change ticket state.

Read [queue semantics](../planfile-execution-gateway.md), [CI completion gates](CI_COMPLETION_GATES.md), and [post-run verification](POST_RUN_VERIFICATION.md) before enabling execution.

<!-- docs:section validation -->
## Validation

Inspect the handler and working directory before running it. Check that the ticket is open, runnable, unblocked and claimable. Use `koru --help` and `koru work next --help` to inspect options without executing tickets.

If claiming fails, check Planfile availability and ticket lifecycle state. If the CLI fails before startup after moving a virtual environment, recreate the environment rather than modifying application behavior.

<!-- docs:section risks -->
## Risks and ownership

Shell handlers have the operator's permissions; review commands, credentials and deployment side effects first. A brief containing a command is not evidence that it ran. Post-run verification is not automatically attached to standalone queue execution.
