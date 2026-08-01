# Changelog

## 2026-08-01

- Initialized governance ticket after explicit user approval.
- Recorded the read-only audit and baseline verification results.
- Enabled deterministic todo2code communication analysis and confined its
  output directory to the target repository.
- Made todo2code tickets human-owned by default; autonomous LLM execution now
  requires both an explicit flag and a named target capability contract.
- Removed direct source-patch self-approval and quarantined patch evidence for
  the Planfile manifest transaction.
- Protected standard and target-manifest governance paths, rejected malformed
  symbol-qualified file targets, and added explicit file-creation support.
- Added Docker-first, multi-command verification using an isolated Compose
  service with no network.
- Added and expanded regression coverage across discovery, scanning, CLI,
  ticket hydration, context construction, transaction gates and governance.
- Published the governed implementation directly to `main` as `4d061d28`.
