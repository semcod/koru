# Ticket 061: Supervise Goal governance remediation

- **ID**: ticket-061
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: VALIDATION
- **Created**: 2026-09-02

## Goal and scope

Add a bounded Koru supervisor for Goal governance failures. Koru runs Goal in
the target repository, resolves stable `GOV-*` diagnostics from the target's
own catalog and runbook, and can hand `GOV-TICKET-001` to one selected agent
before retrying Goal exactly once. Goal remains the policy authority and Koru
must fail closed instead of bypassing governance or widening ticket scope.

## Acceptance criteria

- [x] AC-01: The user's request to continue, implement and test records
      `SESSION_EXECUTION_AUTHORIZATION` for this bounded feature.
- [x] AC-02: `koru goal` runs Goal in the selected project and preserves its
      terminal result while exposing detected governance diagnostics.
- [x] AC-03: `--auto-remediate` launches at most one selected agent only for
      the allowlisted `GOV-TICKET-001` code, then retries Goal exactly once.
- [x] AC-04: The handoff embeds target-owned diagnostic/runbook evidence and
      explicitly forbids destructive changes, scope bypass, push and merge.
- [x] AC-05: Focused tests, Ruff, governance and Docker configuration pass.

## Validation

- 70 focused tests and 52 subtests pass.
- Scoped Ruff, compileall, managed governance, Docker Compose configuration
  and whitespace validation pass.
- A broader run reached 1242 passing tests before an order-dependent,
  out-of-scope `command_picker` failure. The failing test passes alone and the
  complete 19-test module passes on clean accepted base `7b19cf82`; the picker
  source is byte-identical and outside this ticket.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
