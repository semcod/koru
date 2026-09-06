# Ticket 094: MCP startup stdout integrity

- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Owner**: codex

## Goal and scope

A real MCP client reports invalid JSON when the startup activity banner reaches stdout. Send that diagnostic to stderr using the existing activity format option.

## Acceptance criteria

- [x] AC-01: Startup with activity enabled emits only JSON-RPC to stdout and keeps the diagnostic on stderr.
- [x] AC-02: Real subprocess regression, managed governance and stack checks pass before protected publication.

Validation: real subprocess JSON parsing failed before fix. Focused MCP and quality tests, Ruff, managed governance and Compose pass.
