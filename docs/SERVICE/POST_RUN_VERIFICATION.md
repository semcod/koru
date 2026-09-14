---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "post-run-verification",
  "kind": "service",
  "version": 1,
  "title": "Post-run verification",
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

# Post-run verification

<!-- docs:section summary -->
## Purpose and status

Autonomous cycles can verify completed tickets and reopen or block them after a failing check. The feature is disabled by default and is distinct from standalone queue execution.

<!-- docs:section details -->
## Scope and behavior

Configure `koru.yaml`:

```yaml
queue:
  post_run_verify:
    enabled: true
    commands:
      - koru ci run --project .
    on_failure: reopen
    timeout_seconds: 300
    max_output_chars: 800
    after_ide_drive: true
    ide_done_window_minutes: 30
```

Commands run sequentially; the first failure stops the sequence. Native execution uses `/bin/sh -c` in the project directory, with the configured timeout per command. The default is 300 seconds. Custom runners own their timeout enforcement. Timeout returns 124; launch failure returns 127.

Empty or malformed command lists, whitespace-only commands and invalid timeouts produce `not_run`, not success, and do not mutate ticket state. Valid batch verification runs once and associates the result with eligible completed tickets.

On failure, `reopen` requests status `open`; `block` requests `blocked`. Koru verifies the persisted status by reading it back. Failed writes, failed reads or a mismatched status produce `persistence_failed`, not a claimed successful reopen/block.

IDE verification includes pending or recent completions. Session-local `post_verify_seen` deduplicates by ticket ID; it is not bound to attempt, HEAD or verification profile. [CI gates](CI_COMPLETION_GATES.md) remain separately required.

<!-- docs:section validation -->
## Validation

Relevant implementation: `src/koru/autonomy/post_run_verify.py`. Run `python -m pytest tests/test_post_run_verify.py tests/test_post_run_verify_env.py tests/test_post_run_verify_boundaries.py tests/test_post_run_verify_persistence.py`.

Verify the failing-command exit code, persisted lifecycle status and captured diagnostic tail. A `not_run` or `persistence_failed` result requires operator investigation.

<!-- docs:section risks -->
## Risks and ownership

Commands may have side effects and run with operator permissions. Native execution removes KORU_, TILLM_ and VDISPLAY_ variables from its environment; this is not a general secret scrubber. Keep secrets out of command output. Session-local ID deduplication can miss a later completion of the same ticket. Stale in-progress ticket hygiene is a separate mechanism.
