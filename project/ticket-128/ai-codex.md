---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-128
---

# Participant: codex

The user explicitly authorized continuation of the Wellmanifest update
automation. The implementation is deliberately split into a read-only fleet
scan and an optional, serialized Planfile ticket-emission phase.

Constraints:

- the standard source must be a clean local checkout with an exact HEAD;
- no adopter is edited by the scanner;
- dirty repositories and linked worktrees are reported as evidence;
- emitted tickets are waiting-input handoffs, not takeover or merge authority;
- actual adoption remains target-owned and must pass the target gates and
  protected Validator.
