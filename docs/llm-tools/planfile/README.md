# planfile — ticket-driven backlog dla LLM agenta

## Co to jest

YAML-based ticket store + CLI. Każdy ticket ma 7 sekcji LLM-ready
(Context, Reproduction, Affected paths, Acceptance, Constraints, Prompt,
Raw). **W większości LLM-free** — to jest po prostu structured store.

LLM jest używany tylko w `planfile init` (interactive wizard).

## Kiedy używać

| Scenariusz | Komenda | LLM? |
|---|---|---|
| Healing-webhook auto-tworzy ticket z alertu | (auto, przez `ticket_builder.py`) | ❌ |
| Manualne dodanie ticketu | `planfile ticket create "..."` | ❌ |
| Pokaż ticket | `planfile ticket show PLF-021` | ❌ |
| Lista ticketów | `planfile ticket list --status open` | ❌ |
| Aktualizuj status | `planfile ticket update PLF-021 --status done` | ❌ |
| MCP server dla Windsurf | `python3 -m planfile.mcp.server` | ❌ |
| Init wizard nowego projektu | `planfile init` | ✅ |

## Konfiguracja

### `@/home/tom/github/maskservice/c2004/planfile.yaml`

```yaml
name: c2004
project_name: c2004 — Mask Services Monorepo
project_type: webapp
goal: "..."
sprints: [...]
backlog: [...]
```

### Env vars (tylko dla MCP)

```bash
PLANFILE_PROJECT=/home/tom/github/maskservice/c2004    # dla MCP server
```

## Komendy

```bash
# CRUD operacje
planfile ticket list --format yaml | --format table
planfile ticket show PLF-021
planfile ticket create "Fix endpoint X" --priority high --source manual
planfile ticket update PLF-021 --status in_progress
planfile ticket update PLF-021 --status done

# Filtry
planfile ticket list --status open --label llm-ready
planfile ticket list --priority critical
planfile ticket list --label severity:critical

# MCP server (dla Windsurf/Cursor)
python3 -m planfile.mcp.server                          # stdio
```

## Format ticketu (auto-generated)

Każdy ticket wygenerowany przez healing-webhook ma:

```markdown
## 🚨 Context (alert + commit + timestamp)
## 🔁 Reproduction (bash commands)
## 📂 Likely-affected areas (paths)
## 🔍 vallm pre-flight (syntax score per file)
## ✅ Acceptance criteria (checkboxes)
## 🔒 Constraints (do NOT modify)
## 🤖 Prompt (verbatim dla LLM agenta)
## 📎 Raw alert payload (JSON)
```

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/planfile.yaml` | Project config |
| `@/home/tom/github/maskservice/c2004/Taskfile.yml:336-373` | Tasks `tickets:next/list/show/done` |
| `@/home/tom/github/maskservice/c2004/monitoring/healing-webhook/ticket_builder.py` | LLM-ready template |
| `@/home/tom/github/maskservice/c2004/monitoring/healing-webhook/app.py:142-167` | Auto-creation z alertu |
| `@/home/tom/github/maskservice/c2004/.windsurf/mcp_config.example.json` | MCP server entry |

## Workflow w c2004

```
healing-webhook detekuje alert
    ↓ ticket_builder.build_payload()
planfile ticket create (auto, no LLM)
    ↓ ticket w planfile.yaml
Windsurf agent: task tickets:next
    ↓ czyta ticket przez MCP lub CLI
agent edytuje pliki, dodaje test
    ↓ git commit + pre-commit walidacja
task tickets:done -- PLF-021
    ↓ ticket zamknięty
```

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `planfile: command not found` | `pip install --user planfile` |
| `planfile.yaml not found` | `planfile init` lub skopiuj template |
| Tickety nie pokazują się | Sprawdź ścieżkę: `pwd` musi być w c2004 |
| MCP server nie startuje | `python3 -m planfile.mcp.server --help` (debug) |

## Linki

- Repo: https://github.com/semcod/planfile (lokalnie: `/home/tom/github/semcod/planfile`)
- Wersja: `0.1.52` (editable)
- W c2004: 30+ ticketów (PLF-001 … PLF-035) auto-tworzonych
