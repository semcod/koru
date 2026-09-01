# Ticket 024: Synchronize architecture documentation contracts with code

- **ID**: ticket-024
- **Owner**: agent:codex (planning); implementation requires explicit approval
- **Status**: PLAN
- **Workflow state**: WAIT_FOR_APPROVAL
- **Created**: 2026-09-01

## Goal and scope

Synchronize the architecture documentation contracts with the repository at
`main@58c17b255b7e10a590f4aafe08ab011a5b3d847f`. Generate a compact,
machine-readable documentation-conformance DSL from the current code map and
documentation scans, remove current-state references to the deleted
`src/korullm` namespace, and reconcile the associated architecture narratives.

This is the first bounded slice of the requested repository-wide documentation
refresh. It owns one component and ten files under `docs/**`; it does not edit
source, tests, schemas, dependency metadata, root documentation, or generated
files under `project/`.

## Planning baseline

- `autogrammar/sumd` 0.3.60 maps the current checkout to 1,469 code modules,
  264,786 lines, 1,203 Python modules, 8,819 functions, 819 classes, 339
  critical functions and zero dependency cycles.
- The committed `project/map.toon.yaml` is dated 2026-07-29 and reports 1,762
  files / 293,289 lines; it is not owned by any declared implementation
  workstream and will not be silently rewritten by this ticket.
- The three architecture contract tests currently report four failures:
  three derive from the deleted `src/korullm` path and one from a stale map
  header layout.
- `semcod/docval` 0.1.5 scans 95 files / 1,704 sections in `docs/` at 81.3%
  heuristic health, with 9 invalid, 2 outdated and 4 orphaned sections.
- `semcod/code2docs` 3.0.34 reports 14 broken links, 3 malformed tables and
  36 duplicate headings in `docs/`. Two malformed tables are in the
  architecture subtree owned by this slice.

The new conformance DSL will retain the full baseline and the ordered follow-up
slices, so later tickets can improve the remaining documentation against a
stable delta rather than rerunning an unbounded rewrite.

## Acceptance criteria

- [ ] AC-01: The exact-base, ten-document integration scope is explicitly
  approved before any `docs/**` file changes.
- [ ] AC-02: `docs/architecture/documentation-conformance.toon.yaml` records
  reproducible `sumd`, `docval` and `code2docs` provenance, current code-map
  metrics, documentation findings and the remaining bounded work queue.
- [ ] AC-03: The autonomy mutation, dependency boundary and volume-reduction
  DSLs contain only real current source paths and remain schema-valid and
  canonically ordered.
- [ ] AC-04: The three focused architecture contract test modules pass,
  including their existing 857 subtests, without changing tests or runtime
  code.
- [ ] AC-05: Current architecture prose no longer presents `src/korullm` as an
  existing namespace; historical decisions are clearly labelled, and the two
  architecture table-shape findings reported by `code2docs` are resolved.
- [ ] AC-06: Governance, YAML parsing, diff hygiene and Docker configuration
  checks pass; the full documentation audit remains recorded as follow-up
  evidence rather than being hidden.

## Planned follow-up slices

1. Repair the remaining navigation/link findings in top-level `docs/*.md`.
2. Reconcile the 45 mirrored `docs/llm-tools/**` documents with their current
   external tools and remove dead local links.
3. Audit operational guides/specs against actual CLI, configuration and API
   symbols using focused code owners and tests.
4. Open a governance slice for root and currently unowned documentation paths
   before touching `README.md`, package/plugin/example READMEs or generated
   analysis under `project/`.

## Participants

- Human participant: the active user requested the repository-wide audit and
  refresh; identity remains unresolved and no `user-*` file was created.
- Agent participant: [ai-codex.md](ai-codex.md)
