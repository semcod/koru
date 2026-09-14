# Ticket 133: Execute GitHub issue lists sequentially through Koru

- **ID**: ticket-133
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-14

## Goal and scope

`SESSION_EXECUTION_AUTHORIZATION`: the user requested `koru ticket https://github.com/maskservice/c2004/issues/` to execute successive tickets, continuing the authorized implementation, testing and protected publication workflow. Keep the explicit C2004 main-only exception and operator-configured file scope. The previous single-issue implementation was merged through PR #170.

## Acceptance criteria

- [x] AC-01: Accept exact issue-list URLs with or without a trailing slash; select a finite, oldest-first snapshot of open issues across pages and exclude pull requests.
- [x] AC-02: Execute one issue at a time through the existing scoped runner, stop on failed or incomplete delivery, preserve replay receipts, and prevent concurrent repository writers.
- [ ] AC-03: Provide a read-only list preview, test routing/recovery/scope boundaries, and publish through independent OneDev/Validator without executing real C2004 issues as tests.

## Tracking boundary

Private queue and execution receipts remain ignored operational data. Do not alter unrelated primary-checkout changes, broaden execution profiles from remote issue content or bypass protected delivery.

## Verification and publication

139 focused tests and 54 dispatcher subtests passed, including real Git commits
and native Planfile comment recovery with simulated GitHub transport. Ruff,
Docker Compose configuration and the managed governance gate passed. A read-only
preview of C2004 returned issues 7, 12, 16 and 17 in that order; no live issue
execution, hardware command or repository-profile expansion was performed.
Publication remains subject to exact-head OneDev checks and independent Validator
approval. The saved private queue selection survives interruption and closure of
an issue while reporting remains pending.
