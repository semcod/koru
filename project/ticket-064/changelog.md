# Changelog

- Merged the Koru and compatibility Coru text parsers/serializers into the
  canonical `dsl2koru` grammar with both default-context signatures.
- Added a canonical union registry for all 22 command schemas and moved the
  validation codec and Pydantic model generation behind it.
- Replaced six legacy text/schema modules with canonical aliases and added the
  one-release package deprecation warning.
- Removed 209 production Python lines net; cumulative order-30 production
  reduction is 1,067 lines.
- Verified 48/48 DSL tests, both 22-model codegen checks, changed-file Ruff,
  compile, governance, worktree overlap, Docker Compose and diff gates.
