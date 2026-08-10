# Ticket 007: Verify the installed wheel CLI in isolation

- **ID**: ticket-007
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-10
- **Work classification**: `SERVICE / health`

## Goal and scope

Build the Koru wheel and execute its real `koru --version` entry point in an
isolated uv environment that receives only the wheel and its published runtime
metadata. This permanently covers the class of defect found in public Koru
0.1.459, where development dependencies hid an undeclared runtime import.

## Acceptance criteria

- [x] AC-01: The user explicitly authorized autonomous testing, publication
  and continuation without repeated confirmation.
- [x] AC-02: The distribution test builds exactly one Koru wheel from the
  current checkout.
- [x] AC-03: The isolated wheel environment resolves published dependencies
  and `koru --version` reports the version from `pyproject.toml`.
- [x] AC-04: Focused tests, repository governance, hosted smoke and exact-head
  validation pass before merge.

## Risk boundary

This adds one distribution regression test only. It changes no runtime source,
dependency metadata, public interface, CI configuration or release version.

## Validation evidence

- Ruff: PASS.
- Distribution suite: 4 passed, including the isolated installed-wheel CLI.
- Repository governance: 0 errors, 0 warnings.
- Goal 2.1.292: `already-bumped -> 0.1.460`; the test-only follow-up does not
  request another release increment.
- Validator run 31394808302 correctly rejected the initial patch because the
  required uv boundary used an optional skip primitive. The corrective diff now treats a
  missing uv executable as a hard failure in both wheel distribution tests.
- Initial PR `semcod/koru#23` was merged despite a validator
  `CHANGES_REQUESTED` review, exposing a repository protection gap; merge:
  `f3435a3c99bb9f7f1087e38918dbe8255224ff5f`.
- Corrective PR: `semcod/koru#24`; approved exact head:
  `90a6a97529753f379593df3574528ad80c167be3`; validator run:
  `31395677350`; merge commit:
  `5206f00a18a986566cb6c5acf497be0a9b26c5b3`.
- Corrective hosted smoke, distribution suite and exact-head validation: PASS.

## Session authorization

The user authorized autonomous implementation and testing in this session on
2026-08-10. No fresh confirmation is required for this bounded test path.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
