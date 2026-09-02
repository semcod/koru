# Ticket 062: Synchronous planfile GitHub sync on Koru ticket changes

- **ID**: ticket-062
- **Owner**: agent:cursor
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-09-02

## Goal and scope

When Koru creates or updates Planfile tickets (scan, `create_nl_task`,
queue living status, `koru work start`), publish the change synchronously
through Planfile's GitHub/GitLab/Jira/OneDev sync so remote issues show
where Koru is working.

Koru does not call GitHub APIs directly — Planfile remains the sync
boundary (ticket-029 architecture).

## Acceptance criteria

- [x] AC-01: New tickets created via `create_nl_task` trigger Planfile sync when configured.
- [x] AC-02: Living status updates push to configured integrations after description write.
- [x] AC-03: `koru scan --apply` passes `--sync` to `planfile ticket create`.
- [x] AC-04: `policy.yaml` documents the `planfile_sync` block.
- [x] AC-05: focused tests, Ruff, Docker Compose and governance pass after
  rebasing the delivery on the protected CI-history repair.
