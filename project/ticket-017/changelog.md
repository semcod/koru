# Ticket Changelog (ticket-017)

## [0.1.0] - 2026-08-27

- Initial governance scaffold created.
- No human participant identity or content was generated.
- User approval recorded and implementation moved to EDIT on current main.
- Enforced exact MCP ticket execution through the locked queue boundary.
- Added central SubLLM preflight before Planfile lifecycle mutation.
- Added truthful infrastructure/target failure reporting and regression tests.
- Closed the ticket after focused tests, Ruff, governance, Docker, MCP, and
  isolated c2004 validation passed.
- Reopened after the controlled c2004 run exposed that preserved
  `executor.mode: patch` was ignored when deciding whether edits were required.
- Made executor patch mode a durable edit expectation and validated successful
  apply/verify delivery on controlled c2004 ticket PLF-2216.
