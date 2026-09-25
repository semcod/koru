# Ticket 196: Human delegation popup modal and controls for koru serve

- **ID**: ticket-196
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-25

## Goal and scope

Implement human-to-Koru delegation notifications and interactive controls in `koru serve`:
1. When queue tickets require human action (`status: waiting_input` or `executor: human`), notify the operator via browser popup / dialog modal and Web Notifications.
2. Provide modal UI to review ticket details, optionally add operator guidance / instructions / prompt additions, and delegate execution to Koru (SubLLM).
3. Provide backend endpoint(s) to convert tickets to `executor: {kind: "llm", mode: "automatic"}`, set `execution.state: "ready"`, append operator notes, and update sprint files.
4. Support both per-ticket delegation via modal and bulk delegation from waiting input actions.

## Acceptance criteria

- [x] AC-01: Scope is approved by human owner request.
- [ ] AC-02: Backend endpoint `/api/tickets/delegate` and bulk action `delegate` convert ticket to `executor.kind=llm`, `execution.state=ready`, append operator prompt guidance/notes, and persist to sprint.
- [ ] AC-03: Frontend dashboard detects waiting human tickets and triggers browser notification and interactive modal for operator confirmation/input.
- [ ] AC-04: Operator can fill custom instructions / notes and delegate to Koru with one click.
- [ ] AC-05: Unit tests in `tests/test_dashboard_ticket_handlers.py` and `tests/test_dashboard_routes.py` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
