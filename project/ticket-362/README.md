# Ticket 362: Fix local queue project and dry-run boundaries (STARTER-602)

- **ID**: ticket-362
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-29

## Goal and scope

STARTER-602: repair the local queue boundaries around `--project` and
`--dry-run` in `koru ticket auto`:

- An explicit `--project` must be the project root itself. A directory that
  lacks `.planfile/` or `koru.yaml`, a missing path, a plain file or a
  `.git`-only directory must not escalate to a parent project.
- `--dry-run` previews (single ticket and `--loop`) must not produce effects:
  no fake claim/start, no executor invocation, no finalization, no `ticket
  block` for incomplete tickets, no runner-lock artifacts and no
  local-manager session.

## Acceptance criteria

- [x] AC-1: An explicit project never resolves to its parent; non-root paths
  are rejected at the CLI boundary.
- [x] AC-2: Single and loop previews are effect-free, including for an
  incomplete ticket whose action cannot be resolved.
- [ ] AC-3: Independent OneDev/Validator publication of the exact head.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
