# Ticket 152: Apply koru.yaml autonomy strategy defaults to koru autonomous up

- **ID**: ticket-152
- **Owner**: claude
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-16

SESSION_EXECUTION_AUTHORIZATION: after the ticket-144 deployment the user was
shown that `koru.yaml`'s declared `idle_discovery` never reaches the deployed
service and answered "tak, wykonaj" to opening and implementing this fix.

## Goal and scope

`apply_autonomy_strategy_defaults` returns early unless `_invoked_as_auto` is
set, and only the `koru auto` alias sets it. The deployed loop
(`c2004-koru-autonomous.service`) runs `koru autonomous up` directly, so its
`koru.yaml` declaring

```yaml
autonomy:
  strategy:
    idle_discovery:
      enabled: true
      min_interval_seconds: 60
```

never reached `args.scan_after_idle_queue`, which kept the argparse default
`False`. Observed on 2026-09-16: that loop had not run scan-after-idle or the
code2llm/todo2code discovery chain once since 2026-09-15, and sat idle for 65
cycles (~16 h). The strategy file reads as authoritative but is inert for the
exact entry point long-running services use.

Key the defaults on the resolved `up` action instead of the alias flag. Explicit
CLI options must keep winning, so the caller's argv options are now collected
for every `up`, not only for the alias; only the alias still expands the
auto-mode default argument set. Environment overrides such as
`SCAN_AFTER_IDLE_QUEUE` are applied after this step and are unaffected.

## Acceptance criteria

- [x] AC-01: The user's explicit request approves the bounded scope.
- [ ] AC-02: `koru autonomous up` resolves `autonomy.strategy` from the
      project's `koru.yaml` — enabling and disabling `idle_discovery` both take
      effect — while explicit CLI options override it and a project without
      `koru.yaml` keeps the argparse defaults. `koru auto` behaviour is
      unchanged.
- [ ] AC-03: Focused tests, Ruff and governance validation pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
