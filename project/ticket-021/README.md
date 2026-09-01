# Ticket 021: Koru CI publish pipeline

Add `koru ci` for local CI execution and validator-agent publication dispatch.

## Commands

```bash
koru ci run --project .          # policy ci.command + quality gates
koru ci gates --project .        # regix/redup/… only
koru ci publish --ticket ticket-021 --pr 42 --merge --dry-run
```

## Publication config

`.planfile/.koru/ci-publication.yaml`:

```yaml
publication:
  validator_checkout: /home/tom/github/subactor/validator-agent
  wait_checks: true
  merge: false
```

Or set `KORU_VALIDATOR_CHECKOUT`.

## MCP

- `koru_run_ci` with `action=run|gates|publish`
