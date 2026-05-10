# redsl — refactor + quality gate (semcod)

## Co to jest

LLM-driven refactor agent z dwoma podstawowymi trybami:

- **`redsl gate check`** — deterministyczny quality gate (CC, length, forbidden patterns), **LLM-free**
- **`redsl improve`** — LLM-driven incremental refactor (max-actions kontroluje skalę)

## Kiedy używać

| Scenariusz | Komenda | LLM? |
|---|---|---|
| Pre-commit gate przed merge | `redsl gate check` | ❌ |
| Healing-webhook na alercie `severity=error` | `redsl gate check` (DRY_RUN) | ❌ |
| Healing-webhook na alercie `severity=critical` | `REFACTOR_DRY_RUN=true redsl improve . --max-actions 1` | ✅ |
| Manualny refactor pojedynczego katalogu lub modułu | `REFACTOR_DRY_RUN=true redsl improve <path> --max-actions 3` | ✅ |
| Watch mode (autonomiczny daemon) | `redsl watch /mnt/project --mode autonomous` | ✅ |

## Konfiguracja

### Pliki konfiguracyjne

`@/home/tom/github/maskservice/c2004/redsl.yaml` — main config:

```yaml
spec:
  perceive:
    use_code2llm: false      # głębsza analiza
    use_redup: true          # wykrywanie duplikatów
  decide:
    max_actions: 3           # konserwatywnie dla monorepo
    llm_model: auto          # = env LLM_MODEL (default: deepseek-v4-pro)
    include_paths:
      - backend/
      - connect-*/backend/
      - packages/backend-shared-py/
      - frontend/src/
      - firmware/
    exclude_paths:
      - "**/_pb2*.py"
      - "archive/**"
```

### Env vars

```bash
OPENROUTER_API_KEY=sk-or-v1-...           # WYMAGANE dla `improve`
LLM_MODEL=openrouter/deepseek/deepseek-v4-pro   # default model
REFACTOR_DRY_RUN=true                     # zalecane = nie commit'uje patchy
REFACTOR_AUTO_APPROVE=false               # zawsze false w prod
```

## Komendy

```bash
# Gate check — exit 0/non-zero (CI-friendly)
redsl gate check

# Improve — sugestie patchy, dry-run
REFACTOR_DRY_RUN=true redsl improve . --max-actions 3

# Improve — ograniczone do konkretnego poddrzewa
REFACTOR_DRY_RUN=true redsl improve packages/backend-shared-py/src/shared/live_protocol --max-actions 1 --format json

# Watch — daemon (uruchamiany przez docker-compose.quality.yml)
redsl watch /mnt/project --mode suggest --interval 30
```

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/scripts/redsl-gate-precommit.sh` | Pre-commit hook wywołujący `redsl gate check` |
| `@/home/tom/github/maskservice/c2004/.pre-commit-config.yaml` | Hook `redsl-gate` |
| `@/home/tom/github/maskservice/c2004/docker-compose.quality.yml:54-90` | Container `redsl-watch` (autonomous mode) |
| `@/home/tom/github/maskservice/c2004/monitoring/healing-webhook/app.py` | Strategie `heal_redsl_gate`, `heal_redsl_improve` |
| `@/home/tom/github/maskservice/c2004/Taskfile.yml` | Tasks `quality:gate`, `quality:improve` |

## Tryb domyślny vs opt-in w c2004

- **Domyślnie** c2004 używa ścieżki ticket-driven z agentem IDE i bez
  OpenRouter.
- `redsl improve` jest w c2004 **opt-in automation lane**: używaj go do
  testów jakościowej infrastruktury, headless auto-refactorów albo gdy
  user explicite o to prosi.
- Jeśli chcesz tylko sprawdzić jakość patcha w zwykłym flow, zacznij od
  `task quality:regix:local`, `task quality:gate` i `task test`.

### Aktualne ograniczenia lane'a OpenRouter

Na dzień `2026-05-10` lokalny `redsl improve` jest używalny do smoke-testów,
ale pełny server-side automation lane może jeszcze potknąć się o:

- compose / network wiring quality stacka,
- `healing-webhook` uruchamiany bez pełnego `docker` CLI w kontenerze,
- wrappery typu `task monitor:test-heal` lub `task quality:improve`, które
  testują nie tylko `redsl`, ale też otoczenie compose i webhooków.

Jeśli `redsl improve <path>` działa lokalnie, a `task quality:improve` albo
`task monitor:test-heal` nie działa, traktuj to najpierw jako problem
infrastruktury quality lane, nie jako błąd samego refaktora.

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `redsl: command not found` | `pip install --user redsl` lub `bash install.sh` |
| `Error: OPENROUTER_API_KEY not set` | Tylko dla `improve`. Dla `gate check` nie trzeba. |
| `improve` nic nie znajduje | Sprawdź `redsl.yaml` `include_paths` — może plik wykluczony |
| Patches niepoprawnie modyfikują kod | Zawsze zacznij od `REFACTOR_DRY_RUN=true`; w c2004 to preferowany tryb smoke-testów |
| Watch container leci w pętli | `docker logs redsl-watch` + sprawdź `REDSL_INTERVAL_MIN` |

## Linki

- Repo: https://github.com/semcod/redsl (lokalnie: `/home/tom/github/semcod/redsl`)
- Wersja zainstalowana: `1.2.19` (editable install)
- W c2004: `docker-compose.quality.yml`, `redsl.yaml`, `scripts/redsl-gate-precommit.sh`
