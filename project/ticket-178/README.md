# Ticket 178: Audit simple task model routing

- **ID**: ticket-178
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-19

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user asks to investigate whether simple Ruff-generated
work switches to glm-5.3-flash. Planfile request: STARTER-732.
Deliver the Koru-owned [analysis](../../docs/analysis/simple-task-model-routing.md).
Preserve STARTER-617 / ticket-172 and all active application writers.
No runtime model configuration or provider credential change is part of this audit.

## Acceptance criteria

- [x] AC-01: Distinguish configuration, observed execution, model catalog availability,
  ticket source, pricing and measured savings; index and validate the report.

## Session boundary

Owner session codex-model-audit-178-20260919; maxActiveMinutes: 120.
Read-only audit plus isolated documentation delivery; no independent merge authority.

## Accepted follow-up, 2026-09-19

User requests post-fix routing verification and a real SubLLM/Koru log-view test.
This remains a read-only audit plus the existing canonical document. Version2
records the resolver comparison, browser SSE/filter/terminal checks and63 tests.
SubLLM STARTER018 and Koru STARTER734 preserve implementation gaps separately.
Previous-head independent publication stopped before review due to configured
GitHub account API rate limits. No approval or merge bypass is authorized.
