---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "planfile-outbound-sync",
  "kind": "feature",
  "version": 1,
  "title": "Planfile outbound synchronization and profile mapping",
  "status": "implemented",
  "owner": "semcod/koru",
  "scope": "repository",
  "updated": "2026-09-27",
  "source_revision": "2c82e2055feb269399c3081ec6750e5b5ee9b7df",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/koru/commit/2c82e2055feb269399c3081ec6750e5b5ee9b7df",
    "https://github.com/semcod/koru/blob/main/src/koru/planfile_compat.py"
  ]
}
---

# Planfile outbound synchronization and profile mapping

<!-- docs:section summary -->
## Summary

Koru 0.1.461 provides unidirectional Planfile synchronization with GitHub Issues via `planfile sync --direction to` and aligns automated code discovery with structured task execution profiles.

<!-- docs:section details -->
## Details

The planfile integration coordinates local sprint backlogs with remote issue tracking:

1. **Direction-scoped outbound synchronization**: To eliminate race conditions where remote updates overwrite local task queue state, Koru executes synchronization exclusively with `--direction to`. Local tickets in `.planfile/sprints/*.yaml` publish to GitHub without accepting destructive remote pulls into active queues.
2. **Task profile mapping**: Tasks discovered by analysis engines (`code2llm`, `semcod`) map to canonical execution profiles defined in `task_profiles.yaml`:
   - `god_module_split`: Decomposition of overgrown modules exceeding complexity baselines.
   - `cc_hotspot_refactor`: Cyclomatic complexity reduction for critical dispatch paths.
   - `god_function_refactor`: Targeted extraction of oversized functions.
   - `code_smell_refactor`: General hygiene and dead code elimination.
3. **Queue gating and ready checks**: Autonomous execution claims only tickets marked `state: ready` and unblocked by upstream dependencies.

<!-- docs:section validation -->
## Validation

Synchronization and profile behavior are validated by:
- Unit test suite: `pytest tests/test_planfile_compat.py tests/test_planfile_queue.py` verifies sync serialization and state transitions.
- CLI verification: Running `koru scan --all-artifacts` confirms correct profile assignment to newly detected code smells.

<!-- docs:section risks -->
## Risks

- **GitHub rate limits**: Bulk ticket synchronization can consume API quotas; throttled using batching and token rotations.
- **Merge conflict on sprints YAML**: Concurrent sprint edits across branches are avoided by committing sprint modifications in dedicated integration slices.
- **Next steps**: Implement incremental delta sync to publish only modified ticket fields rather than full YAML payloads.
