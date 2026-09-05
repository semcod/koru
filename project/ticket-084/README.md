# Ticket 084: Restore portable package sources and synchronize workspace lock

- **ID**: ticket-084
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-05

## Goal and scope

Fix missing sibling distributions during uv bootstrap and the stale Windsurf
workspace version that npm bootstrap otherwise changes outside source tickets.

## Acceptance criteria

- [x] AC-01: Locked installation needs no sibling repositories; requirements stay unchanged.
- [x] AC-02: Node installation leaves the tracked workspace lock unchanged.
- [ ] AC-03: Governance and package validation pass before protected Goal publication.
