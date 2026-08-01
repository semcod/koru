# Technical directives

Use the current filesystem as the implementation source of truth. Preserve all
unrelated dirty-worktree changes. Apply the governance rules from the external
read-only Governance Hub without writing to that repository.

The implementation must keep generated `project/README.md` untouched, keep
executable code and tests outside this ticket, reject human-owned participant
files as patch targets, and produce auditable manifest-bound execution.
