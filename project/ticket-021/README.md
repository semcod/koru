# Ticket 021: Koru CI publish pipeline

- **ID**: ticket-021
- **Owner**: agent:cursor
- **Status**: PLAN
- **Workflow state**: WAIT_FOR_APPROVAL

Finish and validate `koru ci` for local OneDev verification plus exact-head
validator-agent publication. The initial implementation commits are already on
`main`, but they do not constitute completion evidence for this ticket.

## Acceptance criteria

- [x] AC-01: `koru ci run`, `gates` and `publish` command surfaces exist.
- [ ] AC-02: Ruff and CI pipeline tests pass without the current misplaced
  `dataclasses.replace` import.
- [ ] AC-03: Publication requires local `onedev/local-verify` evidence and
  exact-head validator approval without relying on GitHub Actions capacity.
- [ ] AC-04: Governance, stack and Docker checks pass on the delivery head.

## Planning note

Current-main Ruff reports `replace` undefined in `src/koru/cli_ci.py` and the
same symbol unused in `src/koru/ci/publication.py`. Resume this existing ticket
only after approving its amended intent and moving it to
`IN_PROGRESS / EDIT` in a dedicated branch/worktree.

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
  validator_checkout: ../validator-agent
  wait_checks: true
  merge: false
```

Or set `KORU_VALIDATOR_CHECKOUT`.

## MCP

- `koru_run_ci` with `action=run|gates|publish`
