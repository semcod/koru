# Ticket 088: Prevent Goal downgrade

- **ID**: ticket-088
- **Owner**: tom
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

## Goal and scope
Require published Goal 2.2.0 and update its lock resolution so uv sync does not restore old self-updating CLI code. Wait for the immutable public release before resolving.

SESSION_EXECUTION_AUTHORIZATION: user requested repair and publication through goal -a, with repeated installed-version import failures.

## Acceptance criteria
- [x] AC-01: Every Goal requirement and lock resolution uses at least 2.2.0.
- [ ] AC-02: Locked installation retains the fixed Goal and critical tests/governance pass.
- [ ] AC-03: Protected delivery merges the dependency repair and local Koru goal -a succeeds without changing README.

Validation: uv lock --check and locked fresh installation pass; installed Goal reports 2.2.0 and pending_pull_request_delivery imports successfully. The required costs dependency resolves to 0.2.0. Governance, Docker Compose and whitespace checks pass.
