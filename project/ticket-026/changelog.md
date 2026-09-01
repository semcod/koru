# Ticket Changelog (ticket-026)

## [0.1.0] - 2026-09-01

- Initial governance scaffold created.
- No human participant identity or content was generated.
- Initially preserved the losing governance-plan allocation after concurrent
  PR #55 won ticket 025.
- Replanned ticket 026 before approval when branch audit found PR #56 had been
  merged before protected review.
- Record validator failure `POST_APPROVAL_RECEIPT_MISSING` and the bounded
  two-stage revert/reclosure remedy; implementation remains in
  `WAIT_FOR_APPROVAL`.
- The user explicitly approved ticket 026; workflow moved to
  `IN_PROGRESS / EDIT` before the first-stage reversal.
- Reversed all five PR #56 first-parent effects; ticket-025 evidence matches
  the trusted PR #55 parent and local required gates pass.
- Moved the first stage to `IN_PROGRESS / PUBLICATION` for protected review.
- Opened stage-1 revert PR #57.
- Record protected stage-1 run `33519533252`, exact-head review `5079288844`
  and merge `4de42dc35b6fc3cd883c21fad6fd3760cf6afe00`.
- Reapply ticket-025 closure with truthful incident evidence after the revert.
- Validate both stages with governance, diff and Docker gates and confirm no
  abandoned remote branch remains before stage-2 publication.
- Open stage-2 corrected closure PR #58.

## [0.2.0] - 2026-09-01

- Record successful GitHub smoke and OneDev verification for exact head
  `d7f68633c0a05fde6d024a9e95865765818bdfe2`.
- Record protected validator run `33520531075`, exact-head review `5079395138`
  and merge `f04dbbf1343290a84b0f5ee0176ae0aa9a9ff549`.
- Confirm automatic deletion of the stage-2 topic branch and a remote
  inventory containing only `main`.
- Close the ticket lifecycle as `DONE / DONE` and prepare its governance-only
  closure PR binding.
