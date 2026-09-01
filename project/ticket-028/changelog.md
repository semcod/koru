# Ticket Changelog (ticket-028)

## [0.1.0] - 2026-09-01

- Initial governance scaffold created.
- No human participant identity or content was generated.
- Record the current merge/orchestration audit and immutable new-project
  0.19.19 target.
- Define a bounded adoption, canonical durable-worktree, streamed draft-PR,
  single-freeze and protected-ruleset plan.
- Preserve existing main implementation and isolate ticket-027 recovery work
  outside `/tmp` without merging or discarding it.
- Move ticket-028 itself to the canonical durable
  `<workspace>/.worktrees/koru--ticket-028--merge-streaming` layout with
  byte-identical staged plan evidence and a recovery stash.
- Record terminal ticket-027 evidence and the user's explicit session
  authorization to continue, implement and deploy; enter `IN_PROGRESS / EDIT`.
