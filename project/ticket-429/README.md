# Ticket 429: Consume authenticated admission lease renewal

- **ID**: ticket-429
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-04

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user requests continued repairs, tests and protected merges. Consume the already deployed Autonom renewal endpoint in Koru without issuing policy or widening capability.

## Acceptance criteria

- [x] AC-01: Renewal requires verified HTTPS, exact bindings, unchanged fence/lease identity, advanced CAS revision and a durable accepted or idempotent heartbeat receipt. Lost responses reconcile safely; expired policy or current lease denies authority. The supervised CLI exposes renewal without leaking credentials.
- [ ] AC-02: Native governance, declared stack gates and protected independent exact-head review pass before merge. Record terminal evidence externally, release this lease and clean only this owned worktree.

## Verification and operational evidence

Bounded logs and runtime canaries are preserved externally under the existing wellmanifest operation evidence directory. The foreign primary Planfile cache was restored byte-for-byte; its Git stash is retained for its owner.

## Bounded prerequisite amendment

Critical validation reproduces the unchanged-base CLI dispatch expectation missing seven existing registered commands. SESSION_EXECUTION_AUTHORIZATION covers repairing this three-file slice; scoped admission is free. Preserve strict command equality and verify routing rather than suppressing the failing gate. The previous validation lease is cancelled/released before a fresh scope/plan-bound lease.

## Validation result

22 client tests and 56 subtests passed; the deployed-controller TLS fixture passed acquisition, check, two renewals and idempotent retries. The bounded CLI prerequisite passes 6 tests and 58 subtests. The declared critical suite passes 257 tests; Ruff, governance and Docker Compose validation pass. AC-02 publication remains pending independent exact-head review; no production policy grant is claimed.
