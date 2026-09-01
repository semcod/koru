# Ticket 026: Reconcile the untrusted PR 56 closure merge

- **ID**: ticket-026
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Repair the authorization-order violation introduced when governance-only PR
#56 was merged by a human before the protected validator could approve its
exact head. The validator subsequently failed closed with
`POST_APPROVAL_RECEIPT_MISSING`; the merge therefore cannot be used as trusted
ticket-025 closure evidence despite its correct content and green checks.

The repair is deliberately two-stage. First, a protected exact-head PR reverts
only merge `665bc68eb22f6e98156d540a01fda6976bf0c632`, neutralizing all five
untrusted governance-file effects. Second, a fresh protected exact-head PR
reapplies the same ticket-025 closure evidence and records the incident. No
runtime source, test, dependency, generated Planfile data or implementation
behavior is changed.

## Planning evidence

- PR #55 implementation head `4fb26e742f83349ee8d0a2c66d7672ca9f6cc0ac`
  passed smoke, OneDev and protected review `ifuri-validator-agent[bot]` before
  the validator merged it as `f841c613c7fdb3c51b5147cc50c4d0d8f93bd56b`.
- PR #56 head `b2a9fac8c6382eb25ac7ab234b6356f129f8077a` passed smoke and
  OneDev, but merge `665bc68eb22f6e98156d540a01fda6976bf0c632`
  occurred at `2026-09-01T14:09:58Z` before protected run `33517867410`.
- Run `33517867410` failed with `POST_APPROVAL_RECEIPT_MISSING`; GitHub has no
  protected review for PR #56.
- PR #56 changed exactly `TODO.md` and four ticket-025 evidence files; no
  implementation path was affected.
- GitHub currently reports only `main` plus this ticket-026 plan branch; stale
  topic branches were merged/deleted or closed/deleted.

## Acceptance criteria

- [x] AC-01: A human owner explicitly approves the two-stage repair before any
  ticket-025 lifecycle file is changed.
- [x] AC-02: Apart from the ticket-026 governance scaffold, the first PR is the
  exact first-parent reversal of merge `665bc68e` on its five paths.
- [ ] AC-03: Protected exact-head review and merge complete for the revert
  before any closure evidence is reapplied.
- [ ] AC-04: The second PR restores ticket-025 as `DONE / DONE`, records both
  the trusted PR #55 delivery and the PR #56 incident, and receives protected
  review before merge.
- [ ] AC-05: Final GitHub review evidence binds repository, PR, current head,
  ticket 026 and `ifuri-validator-agent[bot]`; no post-merge approval is used.
- [ ] AC-06: Governance, diff hygiene and Docker Compose checks pass for both
  stages, and remote branch inventory contains no abandoned unique diff.

## Non-goals

- Rewrite or force-push `main` history.
- Retroactively describe PR #56 as trusted.
- Change scan-dedupe implementation delivered by PR #55.
- Mix issue #41, issue #37 or the governance-standard upgrade into this repair.

## Publication

- Stage 1 protected revert: [#57](https://github.com/semcod/koru/pull/57)
- Stage 2 corrected closure: pending successful protected merge of stage 1.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
