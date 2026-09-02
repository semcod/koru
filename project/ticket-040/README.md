# Ticket 040: Harden consumed Docker build inputs

- **ID**: ticket-040
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-01

## Goal and scope

Harden every Docker build input currently consumed by Koru but not owned by
the root image. Adopt the completed Planfile, Regix and TestQL revisions by
immutable commit; pin Python and uv image inputs; and replace mutable pip
resolution in the healing webhook, noVNC, capture and remote-mesh builds with
the repository's frozen uv lock.

## Acceptance criteria

- [x] AC-01: The active user explicitly authorized autonomous continuation and
  sequential closure of the remaining tasks on 2026-09-01 and resumed that
  authorization on 2026-09-02.
- [x] AC-02: Every external Git build context resolves an immutable completed
  upstream revision, and Regix installs only from its frozen portable lock.
- [x] AC-03: Healing webhook, noVNC, capture and remote-mesh images use
  digest-pinned Python and uv inputs with frozen, source-independent installs.
- [ ] AC-04: Compose rendering, each affected build target, targeted smoke
  checks, the managed governance gate and exact-head protected publication
  pass.

## Authorization

`SESSION_EXECUTION_AUTHORIZATION` is recorded from the user's request to
continue autonomously and close all remaining tasks in sequence. It grants no
secret access, self-approval, direct merge or unrelated mutation.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
