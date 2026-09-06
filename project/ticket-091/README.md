# Ticket 091: Add post-run verification deadline

- **ID**: ticket-091
- **Owner**: tom
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION

## Goal and scope

Complete A1 after ticket-090: finite timeout_seconds (300 seconds default) through the sanitized POSIX bounded executor. Injected two-argument runners own their deadlines.

## Acceptance criteria

- [x] AC-01: Invalid deadlines never execute commands; YAML timeout reaches the native executor.
- [x] AC-02: Timeout returns 124, prevents later commands and terminates ordinary POSIX descendants; existing sanitized environment and injected runners remain supported.
- [ ] AC-03: Regression, managed gates and protected publication pass.
