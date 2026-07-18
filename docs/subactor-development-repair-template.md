# Subactor development_defect → Koru repair ticket template

**Template id:** `subactor-development-repair`  
**Packaged file:** [`templates/planfile/subactor-development-repair.yaml.template`](../templates/planfile/subactor-development-repair.yaml.template)

## When to use

Subactor ask or orchestrator hits a **structural** failure (`invalid_runner_response`,
stale step-catalog bug, capability code gap, etc.). The bridge upserts a
`development_defect` on queue `development` and sets `blocked_by` on the source
ticket. Koru picks up a **code repair** ticket — not DNS/Plesk/apply work.

Operational failures (`dns_mismatch`, grant denials, credential issues) stay
in HITL; do not use this template for them.

## Flow

```text
subactor ask "…" --execute --yes          # dry-run only from Koru
  → structural error
  → development_defect (fingerprint dedupe)
  → render subactor-development-repair template
  → planfile ticket import (queue development)
  → Koru patch_mode + worktree + verify
  → branch koru/run-<run_id> promoted
  → human review + merge koru/run-*
  → resume source ticket (preflight → AQL → dry-run → grant → Y/n)
```

Koru **never** runs `subactor ask --apply`, Plesk sync, DNS mutation, or live
connector deploy as part of this template.

## Render (Python)

```python
from koru.queue.ticket_templates import render_subactor_repair_ticket

ticket = render_subactor_repair_ticket({
    "COMPONENT": "orchestrator",
    "ERROR_CODE": "invalid_runner_response",
    "FINGERPRINT": "orchestrator:invalid_runner_response",
    "DISCOVERED_IN": "PLF-364",
    "FILE_1": "orchestrator/bin/subactor-run.mjs",
    "FILE_2": "orchestrator/tests/development-defect.test.mjs",
    "PROMPT_BODY": "Ensure stdout JSON stays valid for large payloads.",
})
# planfile ticket import --source koru-template  (stdin JSON list)
```

## Default patch policy

| Field | Value | Notes |
| --- | --- | --- |
| `patch_mode` | `true` | Agent emits unified diff; Koru applies |
| `promotion_mode` | `branch` | Commit on `koru/run-<run_id>`; main untouched |
| `worktree` | `true` | Staging worktree (+ `KORU_QUEUE_WORKTREE=1`) |
| `max_patch_attempts` | `2` | Mechanical diff retries (not verify failures) |
| `files` | 1–2 paths | Placeholders replaced from bridge `affected_files` |
| `verify_command` | `node --test platform/test/intent-packs.test.mjs` | Local platform unit test from Subactor repo root |

Override `verify_command` per ticket when the defect is outside intent-packs
(e.g. `node --test orchestrator/tests/development-defect.test.mjs`), but keep
commands **local** — no docker compose up, no `--apply`, no Plesk URIs.

## Related

- [Subactor bridge doc](https://github.com/subactor/subactor/blob/main/docs/architecture/subactor-koru-development-bridge.md) (local: `/home/tom/github/subactor/docs/architecture/subactor-koru-development-bridge.md`)
- [ADR-005 transactional workspace](./architecture/adr/005-transactional-workspace.md) — P0 manifest + branch promotion
- [Assessment pointer](./architecture/koru-subactor-autonomy-assessment-pointer.md)
