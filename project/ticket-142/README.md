# Ticket 142: Document adopted Wellmanifest standards in AGENTS instructions

- **ID**: ticket-142
- **Owner**: codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-15

## Goal and scope

Adopt the latest verified `wellmanifest/new-project` release through Goal so
the managed host instructions and governance runtime are refreshed as one
immutable package. This resolves the `AGENTS.md` managed-file drift boundary;
the adoption process, not a hand-edited lock, remains authoritative. The
target-specific standard map stays derived from
`.governance/standard-adoption.json`.

SESSION_EXECUTION_AUTHORIZATION: the user explicitly requested execution,
push and merge in this conversation.

## Acceptance criteria

- [ ] AC-01: The latest verified standard package is adopted through the
      managed updater and its immutable lock is regenerated.
- [ ] AC-02: Refreshed host instructions identify the machine-readable
      adoption authority without duplicating policy prose.
- [ ] AC-03: Managed governance, documentation checks and protected
      exact-head publication pass.

## Blocker

Ticket-065 is still `IN_PROGRESS` in its canonical worktree and has an open
PR #249. Its accepted write scope includes `.governance/manifest.json`, which
overlaps the atomic standard-adoption update required here. Resume ticket 142
after ticket-065 reaches a protected terminal receipt, or after its owner
provides an accepted handoff/reconciliation.

**Update 2026-09-16 (session 2)**: the ticket-065 blocker cleared (PR #249
merged 07:15Z). Work resumed: staged adoption committed (`0766ab7e`), head
refreshed against main (`2d0c6eb8`), `goal governance adopt --latest` confirms
files match 0.20.32 @ `b6ba9c21` exactly; governance gate GOV-PASS. PR #265
opened, but the protected **Koru Docs 0.5** local gate fails on the five
`SNAPSHOT_MIGRATION.md` findings: the 0.20.32 package newly vendors
`docs/information/snapshot-migration.md` into `.governance/docs/` with
`owner: wellmanifest/new-project` and no `scope`, which docs 0.5 rejects
(cross-repository deliverables). The protected job (`check-koru-docs.py`)
hardcodes docs 0.5.0 / revision `71c296aa` with no candidate-selected pin, and
`--managed-copies` (the 0.6.0 exemption for exactly this case) does not exist
in 0.5.0. Upstream `wellmanifest/new-project` at HEAD still ships the same
frontmatter, so this is a cross-standard incompatibility, not a koru content
defect. Hand-edits are forbidden (managed file, lock-bound).

**Blocker (current)**: adoption of 0.20.32 cannot pass protected publication
until one of:
1. `wellmanifest/new-project` ships adopter-conformant vendored docs (or stops
   vendoring into `.governance/docs/`), or
2. the protected koru docs job is upgraded to docs 0.6.0 with a verified
   `--managed-copies` inventory (subactor/onedev-agent protected change).

PR #265 stays open with the failing check as waiting evidence; the branch
holds the complete verified adoption state. Do not re-push an unchanged
effect.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
