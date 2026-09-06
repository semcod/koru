---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-069
---
# Participant: Codex

## Authority

`SESSION_EXECUTION_AUTHORIZATION`: the user explicitly asked to continue,
implement and test after the live Autogrammar validation exposed this defect.
This authorizes only the local implementation and validation in `intent.json`.
It does not authorize destructive changes, secret access, scope expansion,
agent remediation inside Autogrammar, push, merge, tag or publication.

## Plan

1. Resolve direct repositories and explicit contained `--repo` targets.
2. For umbrellas, select only one dirty immediate Git child and otherwise fail.
3. Integrate resolution before Goal and agent construction.
4. Test selection, ambiguity, confinement and subprocess suppression.
5. Re-run the command read-only at the Autogrammar umbrella and all gates.

## Actual changes

- Added direct, explicit and umbrella Git target resolution with path
  confinement and no-shell Git inspection.
- Added structured fail-closed errors and `koru goal --repo`.
- Ensured target resolution completes before Goal or agent construction.
- Added regression coverage for direct, unique dirty, clean, ambiguous,
  missing, escaping and external-symlink cases.
- Confirmed the Autogrammar umbrella now returns 2 and reports all 16 dirty
  candidates without invoking Goal or an agent.
- Passed 81 tests plus 52 subtests, scoped Ruff and compileall.

## Publication authorization — 2026-09-06

SESSION_EXECUTION_AUTHORIZATION: the user answered "kontynuuj" to the concrete request to publish the verified ticket-069 commit through a PR and validator-agent. This extends the earlier local-only scope to protected publication and merge of this Koru change.

Rebased on main 10813e727b88c1f9d808dac326166019d3077d0f. Validation: 82 tests and 52 subtests, Ruff, governance, Docker Compose and whitespace checks pass. Autogrammar resolution reports 16 dirty candidates and requires explicit --repo without launching Goal or an agent.
