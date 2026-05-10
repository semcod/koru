# cursor — IDE alternative do Windsurf

## Co to jest

Cursor (https://cursor.sh) — komercyjny IDE wbudowany na bazie VS Code,
z native LLM agent. **Funkcjonalnie podobny do Windsurf**. W c2004
działa równolegle — możesz mieć tę samą architekturę ticket-driven.

## Kiedy używać

- **Zamiast Windsurf** — jeśli masz subskrypcję Cursor zamiast Windsurf
- **Równolegle** — jeden user na Windsurf, drugi na Cursor — workflow
  jest identyczny (ticket-driven, MCP servers)

## Konfiguracja

### `@/home/tom/github/maskservice/c2004/.cursorrules`

Plik analogiczny do `.windsurf/rules.md` — auto-loaded przez Cursor agenta.

```markdown
# Cursor Rules — c2004

c2004 monorepo używa ticket-driven workflow:

1. `task tickets:next` → highest-priority ticket
2. Czytaj sekcję "📂 Likely-affected areas"
3. Edytuj kod, dodaj regression test
4. `task quality:regix:local` → 0 errors
5. Commit (pre-commit walidacja LLM-free)
6. `task tickets:done -- PLF-XXX`

Domyślnie nie używaj `redsl improve`, `llx fix`, `aider` — używaj
swojego LLM. Wyjątek: gdy user explicite testuje OpenRouter automation
lane lub naprawiasz headless workflow infrastruktury.

Pełen przewodnik: docs/windsurf-agent-guide.md (Cursor i Windsurf
mają identyczny workflow w c2004).
```

### MCP servers

Cursor obsługuje MCP (od wersji `0.45+`). Konfiguracja w:

`~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "planfile": {
      "command": "python3",
      "args": ["-m", "planfile.mcp.server"],
      "env": {"PLANFILE_PROJECT": "/home/tom/github/maskservice/c2004"}
    },
    "testql": {
      "command": "python3",
      "args": ["-m", "testql.mcp.server"],
      "env": {"TESTQL_PROJECT": "/home/tom/github/maskservice/c2004"}
    },
    "redup": {
      "command": "python3",
      "args": ["-m", "redup.mcp_server"],
      "env": {"REDUP_ROOT": "/home/tom/github/maskservice/c2004"}
    }
  }
}
```

## Komendy (w Cursor)

```
@PLF-035 napraw                        — Cursor agent czyta ticket przez MCP
Cmd-K → "fix unused imports"           — Quick edit
Cmd-L → otwórz chat panel              — Pełna konwersacja z agentem
```

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/.cursorrules` | Auto-loaded reguły |
| `~/.cursor/mcp.json` | MCP servers (user home) |
| `@/home/tom/github/maskservice/c2004/Taskfile.yml:332-373` | Tickets workflow (wspólne z Windsurf) |

## Cursor vs Windsurf

| Cecha | Cursor | Windsurf |
|---|---|---|
| Auto-loaded rules | `.cursorrules` | `.windsurf/rules.md` |
| MCP support | ✅ od 0.45 | ✅ |
| Workflow ticket-driven | ✅ identyczny | ✅ |
| Subskrypcja | ~$20/mo | ~$15/mo |
| W c2004 wspierany? | ✅ | ✅ (primary) |

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `.cursorrules` nie ładowany | Reload window: `Cmd-Shift-P → Reload` |
| MCP servers nie startują | Sprawdź `~/.cursor/mcp.json`, restart Cursor |
| Agent nie widzi ticketów | Sprawdź `python3 -m planfile.mcp.server --help` lokalnie |

## Linki

- Cursor: https://cursor.sh
- W c2004: ten sam workflow co Windsurf, patrz `docs/windsurf-agent-guide.md`
