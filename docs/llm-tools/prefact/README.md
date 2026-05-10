# prefact — LLM-aware Python prefactoring

## Co to jest

Linter wykrywający **typowe błędy generowane przez LLM**: relative imports
nie do tego folderu, unused imports z fałszywymi importami, nieukończone
funkcje, hallucinated symbols.

Tryby:
- **Default** — rule-based scan, **LLM-free**
- **Autonomous (`-a`)** — używa LLM do auto-fix tych błędów

## Kiedy używać

| Scenariusz | Komenda | LLM? |
|---|---|---|
| Po patch'u od LLM (Windsurf/Cursor) — sprawdź | `prefact check backend/` | ❌ |
| W pyqual stage `prefact` (przed deploy) | (auto, w pyqual.yaml) | ❌ |
| Auto-fix z TODO list ticketów | `prefact -a` | ✅ |

## Konfiguracja

### `@/home/tom/github/maskservice/c2004/prefact.yaml`

```yaml
exclude:
  - "**/_pb2*.py"
  - "archive/**"
  - "venv/**"
  - "node_modules/**"

checks:
  unused_imports: error
  relative_imports: warning
  hallucinated_symbols: error
  unfinished_functions: warning
```

### Env vars (tylko dla `-a`)

```bash
OPENROUTER_API_KEY=sk-or-v1-...
LLM_MODEL=openrouter/deepseek/deepseek-v4-pro
```

## Komendy

```bash
# Scan (LLM-free) — exit 0/non-zero
prefact check backend/

# Autonomous fix (LLM-driven, używa OPENROUTER_API_KEY)
prefact -a

# Exclude patterns
prefact check . --exclude "**/test_*.py" --exclude "archive/**"

# Z TestQL integration
prefact -a --with-testql
```

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/prefact.yaml` | Konfiguracja (exclude, checks) |
| `@/home/tom/github/maskservice/c2004/pyqual.yaml:59-60` | Stage `prefact` w pipeline |
| Pre-commit (opcjonalnie) | Hook `prefact` (gdyby user chciał) |

## Co prefact wykrywa lepiej niż ruff

| Problem | ruff | prefact |
|---|---|---|
| Unused import | ✅ | ✅ |
| Relative import w niewłaściwym kontekście | ❌ | ✅ |
| Hallucinated function call (np. `os.path.exists_safe()`) | ❌ | ✅ |
| Nieukończona funkcja (`pass # TODO`) | ⚠️ | ✅ |
| Mismatched function signature | ❌ | ✅ |
| Imports jakby były na poziomie pakietu, ale są w submodule | ❌ | ✅ |

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `prefact: command not found` | `pip install --user prefact` |
| Many false positives | Edycja `prefact.yaml` — przenieś check z `error` → `warning` |
| `-a` nic nie naprawia | Sprawdź `OPENROUTER_API_KEY`, sprawdź `LLM_MODEL` |
| Pętla autonomous (3+ iter) | `--max-iterations 1` lub user review |

## Linki

- Repo: https://github.com/semcod/prefact (lokalnie: `/home/tom/github/semcod/prefact`)
- Wersja: `0.1.30` (editable)
