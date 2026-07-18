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

Rendered tickets include **`executor.kind=llm`**, **`inputs.llm_model`** (from
`LLM_MODEL` env when set, else `openai/gpt-4o-mini`), and mirror
`verify_command` into **`acceptance_criteria`** so planfile keeps the gate
command after import.

## Default patch policy

| Field | Value | Notes |
| --- | --- | --- |
| `executor.kind` | `llm` | Headless OpenRouter / vendor CLI patch lane |
| `inputs.llm_model` | `LLM_MODEL` env or `openai/gpt-4o-mini` | OpenRouter prefix stripped at HTTP call |
| `patch_mode` | `true` | Agent emits unified diff; Koru applies |
| `promotion_mode` | `branch` | Commit on `koru/run-<run_id>`; main untouched |
| `worktree` | `true` | Staging worktree (+ template `KORU_QUEUE_WORKTREE=1`) |
| `max_patch_attempts` | `2` | Mechanical diff retries; also `execution.max_attempts` |
| `files` | 1–2 paths | Placeholders replaced from bridge `affected_files` |
| `verify_command` | `node --test platform/test/intent-packs.test.mjs` | Copied to `acceptance_criteria` for planfile |

Override `verify_command` per ticket when the defect is outside intent-packs
(e.g. `node --test orchestrator/tests/development-defect.test.mjs`), but keep
commands **local** — no docker compose up, no `--apply`, no Plesk URIs.

## Planfile import vs Koru queue

Planfile's `TicketInputs` schema **keeps** `llm_model`, `prompt`, and top-level
`executor`, but **drops** Koru-only keys (`patch_mode`, `verify_command`,
`promotion_mode`, …).

On queue drain, `hydrate_subactor_repair_ticket` (label `source:subactor-bridge`)
re-applies the packaged template defaults for stripped patch policy. Verify
resolution order:

1. `inputs.verify_command` (when still present)
2. first runnable `acceptance_criteria` entry
3. `KORU_QUEUE_VERIFY_COMMAND`
4. `koru.yaml` → `when.before_complete_ticket.commands[0]`

**Operator env still optional:**

| Variable | When needed |
| --- | --- |
| `OPENROUTER_API_KEY` + `LLM_MODEL` | Real LLM runs (required) |
| `KORU_QUEUE_VERIFY_COMMAND` | Only if verify is not in `acceptance_criteria` / hydrated inputs |
| `KORU_QUEUE_PROMOTION_MODE` | Only for non-bridge tickets without `inputs.promotion_mode` |
| `KORU_LLM_SHELL_FALLBACK=0` | Force HTTP OpenRouter instead of local agent CLI |

Bridge tickets imported via planfile normally need **no** `KORU_QUEUE_*` overrides.

## Real-LLM pilot (queue intake)

```bash
cd /home/tom/github/semcod/koru
source .env   # OPENROUTER_API_KEY, LLM_MODEL (registry prefix ok)
export KORU_LLM_SHELL_FALLBACK=0
python scripts/subactor-development-repair-pilot.py
```

The script renders `subactor-development-repair` (with `executor.kind=llm`),
imports into an isolated temp git repo, and runs `koru --queue` once. It never
calls Plesk, DNS, or `subactor ask --apply`.

## Related

- [Subactor bridge doc](https://github.com/subactor/subactor/blob/main/docs/architecture/subactor-koru-development-bridge.md) (local: `/home/tom/github/subactor/docs/architecture/subactor-koru-development-bridge.md`)
- [ADR-005 transactional workspace](./architecture/adr/005-transactional-workspace.md) — P0 manifest + branch promotion
- [Assessment pointer](./architecture/koru-subactor-autonomy-assessment-pointer.md)
