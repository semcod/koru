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
- Adopt the complete managed new-project 0.19.19 payload atomically with the
  approved intent and stream it to Draft PR #62.
- Add target-owned package, host-hook and immutable root Docker/Compose
  bindings; preserve the standard-pack seed in truthful audit mode.
- Activate ruleset 22026679 and clean verified merged ticket-027 refs/worktrees.
- Remove the duplicate Koru audit clone through recoverable trash after saving
  its dirty state, then pass the focused overlap and continuity checks.
- Enter `IN_PROGRESS / VALIDATION` with Goal, governance, host, CI-equivalent
  Python and Docker checks passing.
