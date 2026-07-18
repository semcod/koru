# ADR-AD-002: Intent pack + capability contract SSOT

- **Status:** Proposed  
- **Date:** 2026-07-18  
- **Plan:** [`../autonomy-determinism-refactor-plan.md`](../autonomy-determinism-refactor-plan.md) §2–§3.2, PR2–PR3  
- **Subactor reference:** intent packs + `required_capabilities` (no pack-local ALLOW); AQL remains *their* authz — Koru uses JSON Schema / protobuf capability ids instead.

## Context

Koru has policy YAML, MCP tools, IDE command catalogs, and ad-hoc prompt phrases. There is no single versioned catalog of *what the system may intend* and *which capabilities an actor may use*.

## Decision (proposed)

1. **Intent packs** (versioned JSON/YAML) are the SSOT for named goals: `id`, `version`, `phrases`, `situation_schema`, `defaults`, `required_capabilities`, `llm_policy`.
2. Packs **must not** embed allow/deny privilege expansion; they only *declare* required capabilities.
3. **Capability contracts** (per actor / lane / remote peer) are the SSOT for authorization. CI asserts `required_capabilities ⊆ contract`.
4. LLM / planning assistant may **select** a pack and **fill** allowed slots; it may **not** invent shell, URI, or capabilities.

## Consequences

- Dual-run legacy resolvers until phrase maps and MCP catalogs are generated from packs.
- Aligns with Subactor governance without introducing AQL/OQL.
