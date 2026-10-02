# Ticket 425: Preserve staging evidence

- **ID**: ticket-425
- **Owner**: codex-koru-staging
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-10-02

## Goal and scope

SESSION_EXECUTION_AUTHORIZATION: the user requested continued fixes, tests, publication and independent merge. Preserve staging evidence and reject unmanaged staging in governed repositories. Full controller admission and continuous fleet execution remain outside this bounded change.

## Acceptance criteria

- [x] AC-01: Unknown and interrupted worktree evidence survives subsequent queue runs.
- [x] AC-02: Only an unchanged clean detached worktree created by this invocation can be removed normally; no forced removal or global pruning.
- [x] AC-03: Governed primary and linked checkouts refuse unmanaged staging before Git effects; queue returns a refusal rather than a successful execution.

## Tracking boundary

Source and behavioral tests are material delivery. Cross-project findings remain in [the canonical fleet analysis](https://github.com/subactor/docs/blob/main/architecture/analysis/local-ci-adoption.md).

## Validation

Staging and transaction regressions, Ruff, governance and Docker Compose validation pass. The broader local scope has 170 passing tests, 15 passing subtests and three transport failures reproduced on unchanged main; they are not attributed to this staging change. Independent OneDev and Validator checks are required before merge.
