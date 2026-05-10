# llx — intelligent LLM model router (semcod)

## Co to jest

LLM router który wybiera model wg metryki kodu (CC, MI, coupling) lub
explicit tier (`balanced`, `cheap`, `premium`, `free`, `local`). Jedyny
wspólny interfejs do wszystkich providerów (OpenRouter, Anthropic, Ollama).

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Rozmowa z modelem o pliku/projekcie | `llx chat . -p "..."` |
| Auto-fix błędów z metryki | `llx fix . --apply` |
| Sprawdzenie który model byłby optymalny | `llx analyze .` |
| Lista dostępnych modeli z cenami | `llx models --tier balanced` |
| Pyqual integration (stage `fix`) | wywoływane przez pyqual |

## Konfiguracja

### `@/home/tom/github/maskservice/c2004/llx.yaml`

```yaml
models:
  premium:    { provider: anthropic,  model_id: claude-opus-4-20250514 }
  balanced:   { provider: openrouter, model_id: openrouter/deepseek/deepseek-v4-pro }   # default
  cheap:      { provider: anthropic,  model_id: claude-haiku-4-5-20251001 }
  free:       { provider: openrouter, model_id: openrouter/nvidia/nemotron-3-super-120b-a12b:free }
  local:      { provider: ollama,     model_id: ollama/qwen2.5-coder:7b }
  openrouter: { provider: openrouter, model_id: openrouter/deepseek/deepseek-v4-pro }
```

### Env vars

```bash
OPENROUTER_API_KEY=sk-or-v1-...        # default tier 'balanced'
ANTHROPIC_API_KEY=sk-ant-...           # tier 'premium' i 'cheap'
LLX_DEFAULT_TIER=balanced              # tier domyślny
LLX_VERBOSE=true                       # więcej logów
```

## Komendy

```bash
# Quick chat z domyślnym modelem
llx chat . -p "Co robi funkcja sum([1,2,3])?"

# Force konkretny model (pominij router)
llx chat . -p "..." --model openrouter/deepseek/deepseek-v4-pro

# Force tier
llx chat . -p "..." --tier cheap   # użyje claude-haiku

# Auto-fix z errors JSON (pyqual integration)
llx fix . --errors .pyqual/errors.json --apply

# Analiza projektu — który tier byłby optymalny
llx analyze .
# → "balanced (CC=8, MI=72) → use deepseek-v4-pro"

# Lista modeli filtrowanych po tier
llx models --tier balanced --format table
```

## Tiers — kiedy który

| Tier | Provider | Model | Use case | Koszt/run typowo |
|---|---|---|---|---|
| `premium` | Anthropic | claude-opus-4 | Critical refactor, architectural decisions | $0.05-0.20 |
| **`balanced`** | OpenRouter | **deepseek-v4-pro** | **default — większość refactorów** | **$0.001-0.005** |
| `cheap` | Anthropic | claude-haiku-4-5 | Quick formatting, doc fixes | $0.0005 |
| `free` | OpenRouter | nemotron-120b:free | Eksperyment, prototyp | $0 |
| `local` | Ollama | qwen2.5-coder:7b | Offline, prywatne dane | $0 |

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/llx.yaml` | Główna konfiguracja tiers |
| `@/home/tom/github/maskservice/c2004/pyqual.yaml:135-160` | Stage `fix` używa llx z LLM_MODEL=v4-pro |
| Taskfile (manualnie) | `llx chat .`, `llx fix .` |

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `llx: command not found` | `pip install --user llx` lub `bash install.sh` |
| `Provider 'anthropic' has no API key` | `export ANTHROPIC_API_KEY=...` lub uniknij tier `premium`/`cheap` |
| Model timeout (>60s) | DeepSeek V4 Pro czasem 30-60s. Dla quick chat użyj `--tier cheap` |
| Niepoprawne wyniki dla refactoru | NIE używaj `--tier free` ani `cheap` — używaj `balanced` (v4-pro) |
| Ollama nie znaleziony | `--tier local` wymaga `ollama serve` + `ollama pull qwen2.5-coder:7b` |

## Linki

- Repo: https://github.com/semcod/llx (lokalnie: `/home/tom/github/semcod/llx`)
- Wersja: `0.1.49` (editable)
- Modele OpenRouter: https://openrouter.ai/models
