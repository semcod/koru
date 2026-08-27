# Ticket 017: Make MCP ticket execution target-safe and preflighted

- **ID**: ticket-017
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-27

## Goal and scope

Make the existing MCP `koru_run_ticket(project_root, ticket_id, ...)` contract
truthful and fail-closed. A single queue run must execute only the requested
open ticket while holding the queue lock; a missing, closed, filtered, or
otherwise unavailable target must not fall through to another ticket.

For default LLM tickets, probe the central `korullm`/SubLLM queue route before
the ticket is claimed or started. Missing runtime, route, or credentials must
leave Planfile lifecycle state and attempt counters untouched and return an
actionable infrastructure error.

This ticket preserves the provider-neutral runtime merged by ticket-015. It
does not add dependencies, change provider policy, redesign queue priority, or
alter quality-gate policy.

## Acceptance criteria

- [x] AC-01: The human owner explicitly approved the bounded safety scope and
  requested autonomous continuation on 2026-08-27.
- [x] AC-02: MCP passes its required `ticket_id` through the CLI and queue
  command boundary; selection under lock returns that exact open target or a
  non-lifecycle-mutating `target_not_runnable` result.
- [x] AC-03: A nonexistent or unavailable target never executes the next open
  ticket, and MCP no longer emits its former best-effort success note.
- [x] AC-04: The default LLM executor probes `korullm`/SubLLM before
  `ticket claim` / `ticket start`; infrastructure failure does not consume an
  attempt or block/fail the ticket.
- [x] AC-05: Focused regression tests, Ruff, governance, Docker configuration,
  and diff checks pass.

## Session authorization

The user explicitly approved this execution-safety scope and instructed the
agent to continue autonomously. The same scope was first prepared against a
stale local base; it was reallocated as ticket-017 after refresh exposed
already-merged tickets 011-016 and the provider-neutral korullm boundary.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-gpt-5.6-sol.md](ai-gpt-5.6-sol.md)
