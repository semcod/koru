# Ticket 057: Replace small coru adapters with koru aliases

- **ID**: ticket-057
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

Replace the duplicated implementations in the small `cli2coru`, `mcp2coru`
and `rest2coru` adapter families with one-release compatibility namespaces.
Each legacy module must emit a deprecation warning and re-export or alias the
canonical `*2koru` implementation without retaining business logic.

This is the first bounded source slice of order 30,
`namespaces.coru_koru_pairs`, in `docs/architecture/volume-reduction-plan.yaml`.
The user's 2026-09-02 instruction to continue executing the plan under
`docs/*` is `SESSION_EXECUTION_AUTHORIZATION` for this ticket.

## Acceptance criteria

- [x] AC-01: Legacy CLI modules warn and alias the canonical CLI and shell.
- [x] AC-02: Legacy MCP modules warn and alias canonical server and tools.
- [x] AC-03: Legacy REST modules warn and alias the canonical app and CLI.
- [x] AC-04: A compatibility suite proves legacy and canonical identities and command behavior.
- [x] AC-05: The slice removes duplicated production logic and passes Python, governance, overlap, Docker Compose and diff gates.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
