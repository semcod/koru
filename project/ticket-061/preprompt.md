# Preprompt

Implement the bounded `koru goal` supervisor declared in `intent.json`.
Goal remains authoritative. Resolve diagnostics only from the target repository,
launch at most one agent for allowlisted `GOV-TICKET-001`, retry once, and fail
closed. The user's execution request is `SESSION_EXECUTION_AUTHORIZATION` for
this scope only.
