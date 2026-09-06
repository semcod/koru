# Ticket 095: Verify shell task outcome before finalization

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Owner**: codex

## Acceptance criteria
- [x] AC-01: Preserve actual shell output; explicit no-edit or permission-denied results cannot auto-close verified tickets.
- [x] AC-02: Verification succeeds before done; missing or failed verification never transiently completes the ticket.
- [x] AC-03: Regression tests and managed stack gates pass before protected publication.

Validation: 31 finalization/post-run tests pass; Ruff, governance, Docker engine/Compose and whitespace checks pass. Negative prose is a conservative veto, not positive acceptance evidence. Per-ticket material delivery binding remains separate work.
