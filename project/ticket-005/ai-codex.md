---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-005
---
# Participant: codex (AI agent)

## Understanding

Koru synchronizes the Goal development-tool floor through `pyproject.toml`,
`app.doql.less` and `uv.lock`. The adopted manifest owns only the first file,
so deterministic dependency maintenance fails closed on the other two.

## Execution plan

1. Add the existing DSL and lockfile to integration ownership and routing.
2. Update the immutable manifest digest.
3. Run governance and exact diff validation.
4. Deliver an exact-head validated governance-only PR.

## Actual changes

- Added `app.doql.less` and `uv.lock` to integration ownership and routing.
- Updated the manifest lock to the exact customized manifest digest.

## Blockers

- None.
