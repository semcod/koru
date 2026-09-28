# Ruleset approval enforcement migration (ruleset 22026679)

Status: **prepared and independently reviewed**; production deployment is owned
by the live deployment acceptance ticket (successor of the PLF-062 intake).
This document never authorizes modifying the production ruleset, forging
receipts or approving historical merges retroactively.

## 1. Incident (observed 2026-09-27)

- PR542 and PR543 merged with an empty reviews endpoint; PR542 terminal
  reconciliation fails `POST_APPROVAL_RECEIPT_MISSING`.
- PR550 (source `c00548ec`, merged by `tom-sapletta-com` at 19:50:55Z)
  independently confirms the bypass: zero reviews at merge time, OneDev
  evidence absent from the rollup. Merges 551-557 show the same pattern
  (`reviewDecision=""`, no reviews).
- Live readback of ruleset 22026679 (`protected exact-head delivery`,
  `refs/heads/main`, active): `required_approving_review_count=0`,
  `require_last_push_approval=false`, bypass actors `RepositoryRole(5)` and
  `Integration(4344831)` both `always`. Required checks
  `onedev/local-verify` and `standard packs / conformance` with
  `strict_required_status_checks_policy=true` remain correctly configured.
- Baseline snapshot: [fixtures/ruleset-observed-2026-09-27.json](../publication-policy/fixtures/ruleset-observed-2026-09-27.json).

The gap is not missing checks; it is that no independent approval is required
and the operator/admin role can bypass everything.

## 2. Migration profile

Tracked desired body (exact PUT payload):
[ruleset.desired.json](../publication-policy/ruleset.desired.json). Gate:
[ruleset_readback.py](../publication-policy/ruleset_readback.py)
(`readback`, `verify`, `canary`, `--self-test`).

| Field | Baseline | Desired | Why |
| :--- | :--- | :--- | :--- |
| `required_approving_review_count` | 0 | 1 | Minimum independent publication approval. GitHub never counts the pull request author's own review, so a merge needs a second party. |
| `require_last_push_approval` | false | true | The approval must cover the exact head: the last pusher cannot be the approver, so a post-approval push re-blocks the merge until re-approved. Together with `dismiss_stale_reviews_on_push=true` (retained) this is the exact-head review binding. |
| `bypass_actors` | `RepositoryRole(5):always`, `Integration(4344831):always` | `Integration(4344831):always` only | Removes unreviewed admin/operator merging. The Validator App integration bypass is retained because its merges are governed by the independent validator runbook and protected key, outside repository control. |

Unchanged: `deletion` and `non_fast_forward` rules, `refs/heads/main` scope,
`dismiss_stale_reviews_on_push`, `required_review_thread_resolution`,
`require_extra_approval_for_unattributed_changes`,
`allowed_merge_methods=[merge]`, strict required status checks and both check
contexts. The OneDev profile behind `onedev/local-verify` carries the full
test and operating-system matrix; nothing here retires or waives it.

### Admin-bypass assessment

Full removal of `RepositoryRole(5)` (not a downgrade to `pull_request`
bypass): a `pull_request` bypass still allows the role to merge without the
required review, which is exactly the observed defect. Residual risk after
removal: a repository admin can still edit the ruleset itself — GitHub offers
no ruleset that defends against its own editors. Mitigations: the desired
profile is tracked in-repo, `verify` is a one-command drift check, and any
emergency ruleset edit must be followed by a readback and, if the change is
material, its own independent review. Note: the ruleset version-history REST
endpoint returns 404 for the operator token, so version restore requires
ruleset-admin at deployment time; the content-addressed rollback below does
not depend on it.

### Enforcement model after deployment

- Author/operator merges a pull request with zero reviews or a stale approval
  → rejected (validated: HTTP 405, "New changes require approval from someone
  other than the last pusher").
- After an exact-head approving review by the trusted Validator App (or a
  protected `trusted-reviewers` human), checks green, branch current → the
  ordinary account may merge; the App may merge anytime via its bypass.
- No self-approval, no arbitrary-bot trust: only `User` logins in protected
  `trusted-reviewers` or the Bot in `trusted-validator-apps` count as trusted
  review (AGENTS.md 11); the ruleset is the coarse boundary, trusted-actor
  resolution stays with the protected delivery controller.

## 3. Canary evidence (executed 2026-09-27, fork sandbox)

The production ruleset was not touched. A same-account fork
(`tom-sapletta-com/koru`) carried a sandbox ruleset created from the desired
body with two documented deviations: `required_status_checks` dropped (the
sandbox cannot truthfully produce the protected check contexts and no fake
status may be posted) and `bypass_actors` emptied (the Validator App is not
installed on the fork).

Validated records: [evidence/ruleset-canary-fork-2026-09-27.json](../../project/ticket-325/evidence/ruleset-canary-fork-2026-09-27.json)
(`ruleset_readback.py canary` → valid):

1. `ruleset_roundtrip` — the desired body is accepted by the rulesets API and
   reads back conformant (ruleset 24085473).
2. `negative_author_merge_rejected` — the pull request author/operator account
   attempted `PUT pulls/1/merge` on the unreviewed head and was rejected with
   HTTP 405 "New changes require approval from someone other than the last
   pusher"; `mergeable_state=blocked`.
3. `recovery_ruleset_removed` — owner-level `DELETE /rulesets/{id}` plus list
   readback shows the sandbox ruleset absent (emergency-removal mechanics).

Positive App-reviewed canary (deployment ticket): open a canary pull request
on `semcod/koru`, let the Validator App review the exact head, merge, then
capture a `positive_app_reviewed_merge` record and validate with
`ruleset_readback.py canary EVIDENCE --trusted-app-login <validator-app-login>`
(the gate fails closed without the explicit login). Sandbox cleanup note: the
fork could not be deleted through this token (no `delete_repo` scope); it
holds a closed canary pull request, no rulesets and no secrets, and can be
deleted by an account holding that scope.

## 4. Deployment runbook (live acceptance ticket)

1. Pre-flight: `python3 .governance/publication-policy/ruleset_readback.py
   verify` — expect exactly the three baseline gaps; investigate any other
   drift first.
2. Apply: `gh api -X PUT repos/semcod/koru/rulesets/22026679 --input
   <(jq .desired .governance/publication-policy/ruleset.desired.json)`.
3. Readback: `ruleset_readback.py verify` must print `conformant` (exit 0).
4. Canaries: negative (author merge without review rejected on a real pull
   request — do not merge a material branch) and positive
   (`positive_app_reviewed_merge` via the Validator App, exact head).
5. Rollback (tested mechanics, content-addressed): strip the read-only fields
   from the tracked baseline fixture and `PUT` it back:
   `jq 'del(.id,.node_id,.source_type,.source,.created_at,.updated_at,._links,.current_user_can_bypass)' \
   .governance/publication-policy/fixtures/ruleset-observed-2026-09-27.json | \
   gh api -X PUT repos/semcod/koru/rulesets/22026679 --input -`; alternatively
   restore the prior version from ruleset history (needs ruleset-admin).
   Re-run `verify` — it must report the three baseline gaps again, proving
   restoration.
6. Recovery while enforced: a mistakenly blocked merge is recovered by
   obtaining a real exact-head review, never by ruleset relaxation as the
   first move.

## 5. Protected recovery for already-merged unapproved heads

PR542, PR543, PR550 (and any other head merged through the bypass window)
remain unapproved publications. This intake neither forges receipts nor
approves them retroactively. Bounded remediation, in order:

1. Post-hoc independent validation: re-run the validator reconciliation for
   each merged SHA (PR542 already fails `POST_APPROVAL_RECEIPT_MISSING`; the
   PR550 attempt additionally hit an App-lookup API quota limit — retry when
   quota resets). A passing reconciliation recorded against the exact merged
   SHA bounds the exposure without rewriting history.
2. If validation cannot be obtained for a head: revert it and re-land the
   change through the enforced policy (fresh pull request, real exact-head
   review), or
3. Explicit human acceptance of the residual risk for that head, recorded by
   the human owner.

Decision owner for each head: the human operator; agents only prepare and
record the evidence.
