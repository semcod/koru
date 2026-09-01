# Ticket 022: Stabilize Koru work/decide smoke

- **ID**: ticket-022
- **Owner**: agent:codex
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-09-01

## Goal and scope

Stabilize the already-present `koru work` and execution-plan integration after
the delivered `work/decide` implementation introduced two Ruff failures in
the source smoke gate. The repair is limited to removing one unused import and
restoring deterministic import order; it must not change CLI behavior or the
validator-agent authority boundary. Full validation additionally found that
the existing CLI dispatch test omits the delivered `decide` subcommand; the
proposed amendment adds only that test file to reconcile the static registry.

The broader implementation is already on `main`, but presence is not approval
or completion evidence for this bounded repair.

## Acceptance criteria

- [x] AC-01: The amended exact-base, two-source-plus-one-test scope is explicitly
  approved before implementation or test files change.
- [x] AC-02: Ruff passes for both touched modules and for the complete
  `src/koru` smoke scope without suppressions.
- [x] AC-03: Existing execution-plan, work-lifecycle and CLI dispatch regression
  tests are green with no CLI behavior or public-interface change.
- [x] AC-04: Governance, diff hygiene and Docker configuration checks pass on
  the delivery head.

## Planning note

The accepted planning base is `37cd8021034680b6bee7d7ef27c628fef12dddab`.
The user explicitly approved the original two-source-file plan on 2026-09-01;
that slice is preserved in commit `e02bf463`. Full validation exposed a directly
related stale test registry, so the ticket returned to `PLAN / WAIT_FOR_APPROVAL`
for fresh approval of `tests/test_cli.py`. The user approved that amendment on
2026-09-01 and the ticket resumed in `IN_PROGRESS / EDIT`. Conversational
approval authorizes implementation but is not trusted merge authorization.
The unrelated Ruff failure in
`tests/test_autonomous.py` and the seven previously measured deterministic
test failures require separate scopes.

## Participants

- Human participant: explicit conversational approval; identity unresolved and
  no user-* file was created.
- Agent participant: [ai-codex.md](ai-codex.md)
- Agent participant: [ai-cursor.md](ai-cursor.md)

## Publication

- Pull request: [#51](https://github.com/semcod/koru/pull/51)
- Exact head: `8184170855e491f656d4e2710331c37c7a192241`
- GitHub smoke: run `33507425413`, successful.
- OneDev: `onedev/local-verify` passed against
  `main@37cd8021034680b6bee7d7ef27c628fef12dddab`.
- Protected validator: run `33507843823`, result `approved`; review
  `5078036982` by `ifuri-validator-agent` targets the exact head.
- Merge: `8d8531e665c98aa995f53d099ebfb051821ad42e` at
  `2026-09-01T12:31:16Z`.
- Governance closure: [#52](https://github.com/semcod/koru/pull/52)
