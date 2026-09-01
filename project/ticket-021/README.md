# Ticket 021: Koru CI publish pipeline

- **ID**: ticket-021
- **Owner**: unresolved:human
- **Status**: PLAN
- **Workflow state**: WAIT_FOR_APPROVAL
- **Created**: 2026-09-01

## Goal and scope

Finish the already-merged `koru ci` slice without broadening its interface:
move the misplaced `dataclasses.replace` import to its actual consumer, make
the ticket-owned modules Ruff-clean, align command examples with the existing
argparse contract, and add regression coverage for publication overrides.

The initial implementation commits are already on `main`, but they do not
constitute completion evidence for this ticket. Runtime changes stay limited
to the CI/publication boundary declared in `intent.json`.

## Acceptance criteria

- [x] AC-01: `koru ci run`, `gates` and `publish` command surfaces exist.
- [ ] AC-02: A human owner approves this bounded repair.
- [ ] AC-03: `koru ci --project . publish --merge --dry-run` reaches the
  publication boundary without `NameError` and preserves all override flags.
- [ ] AC-04: README examples place the existing global `--project` option
  before the `run`, `gates` or `publish` subcommand.
- [ ] AC-05: Ruff and focused CI/MCP tests pass for every touched module.
- [ ] AC-06: Governance, stack and Docker checks pass on the delivery head.

## Planning note

Current-main evidence is reproducible:

- Ruff reports `replace` undefined in `src/koru/cli_ci.py` and unused in
  `src/koru/ci/publication.py`.
- The documented `koru ci publish --project . ...` form is rejected because
  `--project` is an existing parent-parser option.
- `koru ci --project . publish --merge --dry-run ...` reaches the undefined
  `replace` call.

Resume this ticket only after approval, after ticket-013 lands, and after
moving it to `IN_PROGRESS / EDIT` in its dedicated branch/worktree.

## Commands

```bash
koru ci --project . run          # policy ci.command + quality gates
koru ci --project . gates        # regix/redup/… only
koru ci --project . publish --ticket ticket-021 --pr 42 --merge --dry-run
```

## Non-goals

- Repair unrelated full-suite, autopilot, metadata or generated-map failures.
- Change the `koru ci` option grammar or trust boundary.
- Merge a pull request without protected exact-head authorization.

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

## Participants

- Human participant: unresolved; no `user-*` file was created or modified.
- Agent participants: [ai-cursor.md](ai-cursor.md) and
  [ai-codex.md](ai-codex.md).
