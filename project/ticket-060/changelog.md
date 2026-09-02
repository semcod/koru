# Changelog

- Extended the canonical protobuf envelope with compatibility verbs while
  preserving all existing canonical field numbers.
- Replaced legacy result, event-store and generated protobuf implementations
  with canonical aliases and a thin legacy text-codec wrapper.
- Removed 285 production Python lines net across the consolidated foundation.
- Updated the legacy bus parity test to its current boundary after REST and URI
  adapters became canonical aliases in earlier order-30 tickets.
- Verified 43/43 DSL package tests plus an explicit union-codec/event replay
  probe; repository, Docker, Ruff, compile and diff gates pass.
