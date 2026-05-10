# claude-code — CLI agent z Anthropic

## Co to jest

Anthropic's official CLI agent (https://claude.com/claude-code). Działa
jako headless / interactive agent w terminalu, używając Claude Sonnet/Opus
przez Anthropic API (NIE OpenRouter).

W c2004 jest **alternatywą do Windsurf w trybie headless** — szczególnie
przydatny w CI runners gdzie GUI niedostępne.

## Kiedy używać

| Scenariusz | Komenda | LLM source |
|---|---|---|
| GitHub Actions CI runner | `claude-code` | Anthropic API |
| SSH session bez GUI | `claude-code` | Anthropic API |
| Pair programming w terminalu | `claude-code` | Anthropic API |
| Headless ticket processing | `claude-code "fix PLF-021"` | Anthropic API |

## Konfiguracja

### Auth

```bash
claude-code login      # OAuth flow → token w ~/.claude/auth.json
# lub:
export ANTHROPIC_API_KEY=sk-ant-...
```

### Project config (opcjonalnie)

`@/home/tom/github/maskservice/c2004/.claude/settings.json`:

```json
{
  "model": "claude-opus-4-20250514",
  "permissions": {
    "edit_files": true,
    "run_commands": true,
    "git_commit": false
  },
  "rules_file": "docs/windsurf-agent-guide.md"
}
```

(Claude Code akceptuje rules z dowolnego pliku Markdown.)

## Komendy

```bash
# Interactive session
claude-code

# Headless z prompt
claude-code "Fix unused imports in backend/app/main.py, add regression test"

# Z rules from file
claude-code --rules docs/windsurf-agent-guide.md "Napraw PLF-021"

# CI mode
claude-code --no-interactive --max-turns 10 "..."
```

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/docs/windsurf-agent-guide.md` | Reuse jako rules dla Claude Code |
| `@/home/tom/github/maskservice/c2004/Taskfile.yml` | Tickets workflow (wspólne) |
| (opt) `.claude/settings.json` | Per-project settings |

**Brak** dedykowanej integracji w c2004 — używa tych samych Tasks i
ticketów co Windsurf.

## Claude Code vs Windsurf vs Cursor

| Cecha | Claude Code | Windsurf | Cursor |
|---|---|---|---|
| Środowisko | CLI/headless | IDE (GUI) | IDE (GUI) |
| MCP support | ✅ | ✅ | ✅ |
| Coster | Anthropic (Opus ≈ $0.05-0.20/run) | Subskrypcja | Subskrypcja |
| Tryb autonomous | ✅ `--no-interactive` | ⚠️ wymaga GUI | ⚠️ wymaga GUI |
| Najlepszy do | CI, SSH, headless | Local dev | Local dev |

## ⚠ Koszt

Claude Code używa **Anthropic API directly** — koszty:

- Sonnet: ~$0.003/$0.015 per 1k tokens (input/output)
- Opus: ~$0.015/$0.075 per 1k tokens

Dla typowego ticketu (in:5k, out:2k) → Opus = $0.225, Sonnet = $0.045.

→ Dużo droższy niż Windsurf subskrypcja. **Używaj selektywnie:** tylko
gdy GUI niedostępne lub potrzebujesz Opus quality.

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `claude-code: command not found` | `npm install -g @anthropic-ai/claude-code` |
| `Authentication failed` | `claude-code login` lub `export ANTHROPIC_API_KEY=...` |
| Rate limited | Anthropic API ma limity; sprawdź dashboard |
| Drogi | Użyj Sonnet zamiast Opus: `--model claude-sonnet-4-5` |

## Linki

- Claude Code: https://claude.com/claude-code
- npm: https://www.npmjs.com/package/@anthropic-ai/claude-code
- W c2004: brak dedykowanej integracji, używa wspólnego workflow
