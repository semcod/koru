---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "wellmanifest-worktrees-integration",
  "kind": "information",
  "version": 1,
  "title": "Wellmanifest Worktrees v5 integration and sandbox execution",
  "status": "implemented",
  "owner": "semcod/koru",
  "scope": "repository",
  "updated": "2026-09-27",
  "source_revision": "2c82e2055feb269399c3081ec6750e5b5ee9b7df",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/koru/commit/2c82e2055feb269399c3081ec6750e5b5ee9b7df",
    "https://github.com/wellmanifest/worktrees/blob/44f1686dd041554649720e171d690944afa49586/docs/information/worktree-layout.md"
  ]
}
---

# Wellmanifest Worktrees v5 integration and sandbox execution

<!-- docs:section summary -->
## Summary

Koru 0.1.461 adopts Wellmanifest Worktrees v5 (package 0.5.2) across all autonomous task lifecycles, ensuring strict isolation between the primary checkout, delivery worktrees, and ephemeral execution sandboxes.

<!-- docs:section details -->
## Details

Worktree orchestration follows these mandatory rules:

1. **Path and ref mapping**: Delivery worktrees reside exclusively at `<primary>/.worktrees/ticket-NNN--description` attached to branch `ticket/NNN-description`. Directory names never contain branch slashes, and nested `.worktrees` directories are strictly prohibited.
2. **Atomic lease allocation**: Before branch creation or worktree initialization, an atomic lease is established at `<primary>/.subactor/leases/ticket-NNN--description.json` via `./project/new-ticket.sh`.
3. **Primary checkout protection**: Autonomous cycles never commit to `main` or operate on dirty primary checkouts. All file mutations, tests, and commit actions take place within the allocated worktree.
4. **Twinerd sandbox execution**: For non-delivery dry-runs and exploratory task discovery, Koru invokes `create_twinerd_sandbox` inside `/tmp/twinerd-sandboxes`, providing copy-on-write zero-risk workspaces.
5. **Git configuration**: Worktrees are configured with `worktree.useRelativePaths=true` and `/.worktrees/` is ignored at repository root.

<!-- docs:section validation -->
## Validation

Worktree conformance is verified via:
- Governance gate: `python3 .governance/worktree_path_check.py --root .` validates layout and path rules.
- Published planner check: Execution of `operations/conformance.py` confirms absence of orphaned or misregistered checkouts.
- Git porcelain listing: `git worktree list --porcelain` matches registered leases in `.subactor/leases/`.

<!-- docs:section risks -->
## Risks

- **Worktree proliferation**: High ticket volume may accumulate stale worktrees. Remediated via lifecycle pruning after PR merge.
- **Orphaned leases**: Abrupt host termination could leave lingering lease locks. Handled via lease expiration timeouts and CAS checks.
- **Next steps**: Automate post-merge worktree pruning in the autonomous loop upon detecting merged PR heads.
