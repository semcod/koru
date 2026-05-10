# aider — interactive LLM coder (dockerised)

## Co to jest

Tradycyjny LLM coding agent (https://aider.chat). Wywoływany interactively
lub jako autoloop. W c2004 dostępny **głównie jako fallback** gdy Windsurf
nie jest dostępny (np. w CI runner).

> **Preferred:** używaj **Windsurf agent** (subskrypcja, $0/ticket).
> Aider używaj tylko gdy Windsurf nie ma dostępu (CI, headless, dockerised).

## Kiedy używać

| Scenariusz | Komenda | Preferred? |
|---|---|---|
| Manualna sesja w terminalu | `aider --model ...` | ❌ Windsurf lepszy |
| Headless autoloop w Docker | `task aider:loop` | ✅ jeśli brak GUI |
| CI runner (GitHub Actions) | `aider --yes ...` | ✅ jedyna opcja |
| TestQL stabilization loop | `.windsurf/workflows/aider-docker-autoloop.md` | ✅ alternatywa do Windsurf |

## Konfiguracja

### `@/home/tom/github/maskservice/c2004/.aider/docker-compose.yml`

```yaml
services:
  aider:
    build: { context: .., dockerfile: .aider/Dockerfile }
    environment:
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
      AIDER_MODEL: ${AIDER_MODEL:-openrouter/deepseek/deepseek-v4-pro}
    command: >
      aider --model ${AIDER_MODEL:-openrouter/deepseek/deepseek-v4-pro}
            --yes
            .windsurf/workflows/testql-autoloop.md
            .testql/autoloop-state.json
```

### Env vars

```bash
OPENROUTER_API_KEY=sk-or-v1-...
AIDER_MODEL=openrouter/deepseek/deepseek-v4-pro    # default w c2004
```

## Komendy

```bash
# Jednorazowy run (dockerised)
docker compose -f .aider/docker-compose.yml run --rm aider

# Autoloop (workflow)
task aider:loop                         # uruchamia testql-autoloop

# Konkretny model override
AIDER_MODEL=openrouter/anthropic/claude-opus-4 task aider:loop

# Z konkretnym promptem
docker compose -f .aider/docker-compose.yml run --rm aider \
    aider --message "fix imports in backend/app/main.py"
```

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/.aider/docker-compose.yml` | Container config |
| `@/home/tom/github/maskservice/c2004/.aider/Dockerfile` | Image build |
| `@/home/tom/github/maskservice/c2004/.aider/prompts/` | Re-usable prompts |
| `@/home/tom/github/maskservice/c2004/.windsurf/workflows/aider-docker-autoloop.md` | Workflow |
| `@/home/tom/github/maskservice/c2004/.windsurf/workflows/testql-autoloop.md` | Workflow główny |

## Aider vs Windsurf — kiedy użyć

| Sytuacja | Aider | Windsurf |
|---|---|---|
| Local dev (masz IDE otwarte) | ❌ | ✅ |
| Headless server bez GUI | ✅ | ❌ |
| GitHub Actions CI runner | ✅ (jedyne) | ❌ |
| Long-running autoloop (TestQL) | ✅ docker | ⚠ wymaga otwartej sesji |
| Cost optimization | ❌ płatne | ✅ subskrypcja |
| Quick code review | ❌ | ✅ MCP |

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| Container nie startuje | `docker logs aider-aider-1`; sprawdź `OPENROUTER_API_KEY` |
| `--yes` accepts złe patche | Dodaj `--no-auto-commits`, review manualnie |
| Loop nie kończy | Aider w autoloop może hang'ować — set timeout |
| Drogi (powyżej $1/run) | Sprawdź który model: `AIDER_MODEL=openrouter/deepseek/deepseek-v4-pro` |

## Linki

- Aider: https://aider.chat
- Aider repo: https://github.com/Aider-AI/aider
- W c2004: workflows `.windsurf/workflows/aider-docker-autoloop.md`
