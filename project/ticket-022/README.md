# Ticket 022: Koru work start/finish workflow

- **ID**: ticket-022
- **Owner**: agent:cursor
- **Status**: PLAN
- **Workflow state**: WAIT_FOR_APPROVAL
- **Created**: 2026-09-01

## Goal and scope

Finish and validate the already-present `koru work start/finish` lifecycle that
binds a Planfile ticket, local branch, local CI, and validator-agent
publication. The initial implementation is on `main`, but it was merged while
this ticket still had an invalid, unapproved intent; presence is not completion
evidence.

## Acceptance criteria

- [ ] AC-01: The amended bounded scope is approved before repair work.
- [ ] AC-02: Start creates and synchronizes the ticket before local and remote
  branch creation, without granting merge authority.
- [ ] AC-03: Finish runs local verification and delegates exact-head review and
  explicit merge to validator-agent without depending on GitHub Actions.
- [ ] AC-04: Focused tests, Ruff, governance and Docker checks pass on the
  delivery head.

## Planning note

Resume this existing ticket only from `IN_PROGRESS / EDIT` in its own
branch/worktree after ticket 021 is terminal. Do not treat commits already on
`main` as approval or exact-head validation evidence.

## Participants

- Human participant: unresolved; no user-* file was created.
- Agent participant: [ai-cursor.md](ai-cursor.md)
