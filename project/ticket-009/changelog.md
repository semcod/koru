# Ticket Changelog (ticket-009)

## [0.1.0] - 2026-08-16

- Initial governance scaffold created.
- No human participant identity or content was generated.
- Added a fail-closed Cursor SDK adapter driven by SubLLM's strict Koru routes.
- Routed planning, shell prompts and queue execution to Cursor Grok 4.6 xhigh.
- Removed enforced monetary budgets, default context truncation and transport
  output-token fields while preserving timeouts, retries, patch isolation,
  secret exclusion and verification.
- Removed Qwen3 Coder Next and GPT-4o Mini from Koru runtime defaults.
- Verified live planning JSON and unified-diff generation without write tools.
