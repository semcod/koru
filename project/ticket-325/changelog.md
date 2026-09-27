# Changelog — ticket-325

## 2026-09-27 (PLF-064 intake)

- Captured live baseline of ruleset 22026679 (`required_approving_review_count=0`,
  `require_last_push_approval=false`, `RepositoryRole(5)` + `Integration(4344831)`
  always bypass) as the tracked fixture; confirmed PR542/543/550 merged with
  zero reviews.
- Added the desired profile (1 exact-head approving review, last-push approval,
  admin bypass removed, Validator App integration bypass and all required
  checks preserved) and the read-only `ruleset_readback.py` gate with
  `--self-test` (15 cases), `verify` (baseline: exactly 3 gaps) and `canary`.
- Fork sandbox (`tom-sapletta-com/koru`): created the ruleset from the desired
  body (round-trip conformant), author merge on the unreviewed head rejected
  with HTTP 405 "New changes require approval from someone other than the last
  pusher", ruleset removal recovery confirmed; records validated by the gate.
- Sandbox cleanup partial: PR closed, branch and ruleset deleted; the fork
  itself could not be deleted through this token (no `delete_repo` scope) —
  harmless residue, documented in the migration doc.
- Production ruleset version-history endpoint returns 404 for the operator
  token; rollback therefore documented as content-addressed baseline PUT plus
  optional version restore under ruleset-admin.
- Migration, canary, deployment runbook and unapproved-heads recovery
  documented in `.governance/docs/RULESET_APPROVAL_MIGRATION.md`.
