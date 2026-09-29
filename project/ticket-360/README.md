# Ticket 360: windsurf autopilot plugin accepts Devin Desktop host

- **ID**: ticket-360
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-29

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: user asked to continue Koru autopilot
integration ("kontynuuj"). Devin Desktop reports `vscode.env.appName` as
"Devin", so the windsurf autopilot VSIX activated then aborted silently —
the daemon never saw a plugin. Teach both the `isHost` gate and the IDE
strategy `detect` to treat Devin as the windsurf lane via a shared
`isWindsurfLaneHost` predicate, with a compiled node test.

## Acceptance criteria

- [ ] AC-01: `isWindsurfLaneHost`/`detectIdeViaStrategies` accept Devin and Windsurf, reject other hosts.
- [ ] AC-02: npm test (compile + node tests) passes; governance-check passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
