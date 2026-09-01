# Ticket preprompt

- **Task ID**: ticket-028
- **Task title**: Adopt resumable conflict-safe merge streaming
- **Created**: 2026-09-01T15:11:21Z

Keep executable implementation outside this governance/evidence directory.
Read a human-owned user-*.md file only when one exists.

Preserve `main@d4c3075f` as the accepted baseline. Use published
`wellmanifest/new-project` 0.19.19 only at exact commit
`43999c793a86084b4c3198fe07be350105db59ec`. Never create a linked worktree in
`/tmp`; use the canonical durable `<workspace>/.worktrees` layout.
