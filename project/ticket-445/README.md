# Ticket 445: Report actual SubLLM model in queue execution evidence

- **ID**: ticket-445
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-08

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user requested autonomous service and bug fixing, verification of Willman/Koru/SubLLM/OpenCode and protected delivery. Intake: paxlet-com/willman PLF-113, bounded follow-up PLF-115. A real local GPT-OSS response was labeled cursor/grok-4.6 by the queue summary. Correct the label from the runner result without changing execution or admission.

## Acceptance criteria

- [x] AC-01: The executed result model wins over the requested/default model; legacy runners retain fallback labels and exit codes.
- [x] AC-02: Targeted regression and managed governance checks pass.
- [ ] AC-03: Exact-head OneDev and independent Validator approve protected publication.

## Evidence

External receipt set: receipt:minis-autonomy-20261008/koru-provenance. Source scope: src/koru/queue/runner.py and tests/test_queue_model_provenance.py. No fleet writer is enabled by this change.

Targeted regression: 45 passed. Managed governance: PASS, 0 warnings. Source/test lint: PASS. Protected exact-head CI and independent merge approval remain required.
