# Ticket 025: Deduplicate scan tickets across Planfile history

- **ID**: ticket-025
- **Owner**: agent:codex under the current user continuation request
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Prevent repeated `koru scan --apply` cycles from recreating the same finding
after its Planfile ticket moves from the current sprint into history. Dedupe
must use producer identity plus stable signal/evidence identity, not a bare
title alone, and must still permit a new ticket when the underlying evidence
fingerprint changes.

The change is limited to scan-ticket discovery and tests. It does not rewrite
Planfile history, close or reopen tickets, or change the separate
`koru work start/finish` lifecycle delivered by ticket-022.

This ticket replaces a colliding local allocation of `ticket-024`. Concurrent
PR #53 reserved that ID first for documentation conformance. The reticketing
does not change the already reviewed outcome, paths or architecture.

## Acceptance criteria

- [x] AC-01: The bounded plan is explicitly approved before implementation.
- [x] AC-02: Scan dedupe reads matching current and historical Planfile tickets,
      including history locations referenced by the Planfile index.
- [x] AC-03: A terminal ticket suppresses an identical producer, dedupe key and
      evidence fingerprint, so repeated scans cannot create archival clones.
- [x] AC-04: Changed evidence remains eligible for a new regression ticket; a
      closed title alone never suppresses materially new evidence.
- [x] AC-05: Tickets from unrelated producers and malformed/untrusted history
      entries cannot become dedupe authority.
- [x] AC-06: Focused tests, Ruff, governance and Docker configuration checks
      pass on the exact delivery head.

## Validation result

The focused scan suite passes 76/76. Owned-path Ruff, governance, Docker
configuration and diff hygiene pass. A read-only replay against the umbrella
Planfile loaded 62 historical keys and correctly suppressed all 33 current
suggestions whose producer, dedupe key and artifact fingerprint were identical;
the changed-evidence test confirms a new artifact SHA remains eligible.

## Participants

- Human participant: the user supplied the audit and continuation request in
  the active session; no `user-*` file was created or modified.
- Agent participant: [ai-codex.md](ai-codex.md)
