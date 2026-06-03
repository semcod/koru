# AI tool support roadmap (2026)

Goal: let `koru` orchestrate *all practically relevant* AI coding tools in a stable way,
without coupling core logic to fragile vendor APIs.

## Support model

Every tool should be classified into one of three lanes:

1. **Native lane**
   - First-class `koru` integration (`agent` / `autopilot` / structured health checks).
   - Requires stable invocation and deterministic behavior.

2. **Adapter lane**
   - Executed via `planfile` tickets (`executor.kind=shell|api|llm`).
   - Default for tools with unstable CLI/API or preview lifecycle.

3. **Manual lane**
   - No reliable automation surface yet.
   - Documented usage only.

Promotion path: `manual -> adapter -> native`.

---

## Target inventory (from 2026 ecosystem)

### IDE/Editor tools

- Cursor
- Windsurf
- Zed
- GitHub Copilot (plugin lane)
- Antigravity (preview)
- Kiro
- Junie (JetBrains AI)

### CLI agents

CLI-agent registry, detection, prompt contracts, and execution live in
`/home/tom/github/semcod/sllm`. Koru consumes them through `koru.sllm_bridge`.

- Claude Code
- Aider / Aider Chat
- Gemini CLI
- Codex CLI
- Cline
- OpenCode
- Qwen Code

### Plugin tools

- Copilot plugin family
- Tabnine
- Gemini Code Assist
- CodeWhisperer
- Cody

### App builders / no-code lanes

- Replit
- Lovable
- Bolt.new
- v0
- Teta
- Base44
- NxCode

### Specialist tools

- DeepSeek (model/provider lane)
- NotebookLM
- Perplexity
- n8n
- Grammarly

---

## Execution phases

## Phase 1 — Canonical registry + capability detection

Deliverables:
- `docs/ai-tool-registry-2026.yaml` for GUI, plugin, SaaS, and specialist tools.
- `sllm.compat.tool_registry_entries()` for shell LLM clients, with fields:
  - `tool_id`, `category`, `lane`, `detect`, `invoke`, `stability`, `notes`.
- `koru tools detect --format json` (new command) to report detected tools and lane.
- Handoff markdown uses the combined registry as the source of truth.

Exit criteria:
- 100% tools from target inventory present in the combined Koru + SLLM registry.
- Detection coverage >= 90% for local CLI/IDE tools.

## Phase 2 — Adapter lane for all non-native tools

Deliverables:
- Templates for `planfile` shell/api tickets per tool category.
- `koru task --tool <tool_id>` helper that scaffolds a safe adapter ticket.
- Guardrails: timeout, retries, output truncation, deterministic exit mapping.

Exit criteria:
- Every non-native tool has at least one tested adapter path.
- Adapter templates documented in `docs/cli-examples.md`.

## Phase 3 — Native lane expansion (highest ROI; shell clients via SLLM)

Priority candidates:
1. Gemini CLI
2. Cline
3. Qwen Code
4. OpenCode
5. Zed deep integration
6. JetBrains-native AI channels (Junie-equivalent route)

Deliverables:
- Native launcher + health command per promoted tool.
- Autopilot routing hooks where meaningful.
- Regression tests per promoted tool (mocked + environment smoke).

Exit criteria:
- Native support for top 8 actively used tools.
- No regression in existing lanes.

## Phase 4 — IDE plugin ecosystem bridge

Deliverables:
- Unified plugin bridge contract for Copilot/Tabnine/Gemini/CodeWhisperer/Cody.
- Compatibility table: features available by plugin host (VSCode/JetBrains/Zed).
- Scaffolded bridge tickets via `koru task --tool <plugin-id>` with explicit bridge metadata.

Exit criteria:
- At least read-only status + invoke capability for each plugin family.

## Phase 5 — App builder + workflow automation lane

Deliverables:
- Adapter packs for Replit/Lovable/Bolt/v0/Teta/Base44/NxCode.
- n8n integration templates for ticket-triggered automations.

Exit criteria:
- End-to-end demo: `koru` ticket -> app builder change -> validation report.

---

## Governance and quality bar

A tool can be marked **native** only if all are true:
- deterministic invocation contract,
- non-interactive mode available,
- test harness in CI,
- documented failure taxonomy,
- security review (key handling, command injection surface).

If any of the above is missing, keep it in **adapter** or **manual** lane.

---

## Short answer to "does koru support all tools in 2026?"

Not yet as native integrations.

Current strategy is deliberate:
- broad coverage via adapter lane first,
- native integration only for tools that are stable and testable.
