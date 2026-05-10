# LLM tools — index dla c2004

Każdy podfolder zawiera **README.md** (jak skonfigurować, kiedy używać) i
**install.sh** (idempotent, ~30 linii) dla pojedynczego narzędzia.

## Filozofia konfiguracji

c2004 używa pojedynczego env var `LLM_MODEL` jako **single source of truth**
dla domyślnego modelu (obecnie `openrouter/deepseek/deepseek-v4-pro`,
ustawione 2026-05-10 po empirycznym A/B teście — patrz
[`docs/SESSION-2026-05-09-summary.md`](../SESSION-2026-05-09-summary.md)).

Wszystkie narzędzia LLM-driven dziedziczą ten model przez:

- env var `LLM_MODEL` (lub specyficzny — `PFIX_MODEL`, `AIDER_MODEL`,
  `REFACTOR_LLM_MODEL`)
- config plik tool'a (`pyqual.yaml`, `redsl.yaml`, `llx.yaml`)

## Mapa narzędzi — według warstwy

```
WYKRYWANIE (LLM-free):              ROZWIĄZYWANIE (LLM):           WALIDACJA (LLM-free):
  regix     [regression]              llx       [model router]       ruff       [linter]
  redup     [duplicates]              pfix      [error fix]          pytest     [tests]
  prefact   [LLM-aware lint]          aider     [interactive]        regix      [regressions]
  testql    [declarative scenarios]   redsl     [quality gate +      vallm      [tier-1 syntax]
  planfile  [ticket store]                       improve]
  vallm/1   [syntax check]            windsurf  [primary IDE,
                                                 reuses agent LLM]
  
  ALTERNATIVES:
    cursor       [IDE alternative to Windsurf]
    claude-code  [CLI agent alternative]
```

## Ranking wymaganej konfiguracji

| Tool | Wymaga API key? | Specyficzna config? | Folder |
|---|---|---|---|
| **redsl** | ✅ OPENROUTER_API_KEY | ✅ `redsl.yaml` | [`redsl/`](./redsl/) |
| **llx** | ✅ OPENROUTER_API_KEY | ✅ `llx.yaml` (tiers) | [`llx/`](./llx/) |
| **pfix** | ✅ OPENROUTER_API_KEY | ✅ `PFIX_*` env | [`pfix/`](./pfix/) |
| **vallm** | optional (tier-2) | brak | [`vallm/`](./vallm/) |
| **prefact** | optional (autonomous) | ✅ `prefact.yaml` | [`prefact/`](./prefact/) |
| **aider** | ✅ OPENROUTER_API_KEY | ✅ docker-compose | [`aider/`](./aider/) |
| **planfile** | optional (init) | ✅ `planfile.yaml` | [`planfile/`](./planfile/) |
| **testql** | brak | ✅ scenariusze YAML | [`testql/`](./testql/) |
| **regix** | brak | ✅ `regix.yaml` | [`regix/`](./regix/) |
| **redup** | brak | brak | [`redup/`](./redup/) |
| **windsurf** | (subskrypcja IDE) | ✅ `.windsurf/rules.md` | [`../windsurf-agent-guide.md`](../windsurf-agent-guide.md) |
| **cursor** | (subskrypcja IDE) | ✅ `.cursorrules` | [`cursor/`](./cursor/) |
| **claude-code** | ✅ ANTHROPIC_API_KEY | ✅ `.claude/` | [`claude-code/`](./claude-code/) |

## Quick install (wszystko)

```bash
# Z głównego katalogu c2004
for tool in redsl llx pfix vallm prefact planfile regix redup testql aider; do
  bash docs/llm-tools/$tool/install.sh
done
```

Każdy `install.sh` jest **idempotentny** — bezpiecznie uruchamiać wielokrotnie.

## Jak to jest używane w c2004

Te narzędzia nie są w repo "obok siebie". One tworzą wspólny workflow z
dwoma trybami:

- **Default path** — ticket-driven development z agentem IDE
  (Windsurf/Cursor/Claude Code), bez zdalnych wywołań LLM.
- **Opt-in automation lane** — narzędzia LLM-backed (`redsl improve`,
  `llx`, `aider`) do smoke-testów, jakościowej infrastruktury i
  headless auto-fixów, tylko gdy user explicite tego chce.

W praktyce wygląda to tak:

1. **Wykrywanie**  
   `task monitor:probe`, Prometheus i `healing-webhook` wykrywają błędy i
   zapisują je jako tickety w `planfile.yaml`.

2. **Rozwiązywanie**  
   Agent IDE zaczyna od:

   ```bash
   task tickets:next
   ```

   i pracuje według:

   - [`../windsurf-agent-guide.md`](../windsurf-agent-guide.md)
   - [`../../.windsurf/rules.md`](../../.windsurf/rules.md)

3. **Walidacja**  
   Przed zakończeniem patcha agent powinien przejść co najmniej:

   ```bash
   task quality:regix:local
   bash scripts/regix-precommit.sh
   task test
   ```

4. **Domknięcie**  
   Po fixie ticket zamykamy:

   ```bash
   task tickets:done -- PLF-XXX
   ```

### Current caveats

Default ticket-driven path jest stabilniejszy niż opt-in automation lane.
Jeśli problem wychodzi w:

- `task quality:improve`
- `task monitor:test-heal`
- `healing-webhook` + `redsl_improve`

to najpierw traktuj to jako problem infrastruktury refaktoryzacji
(compose / webhook / quality stack), a nie jako błąd produktu.

## Repo entry points dla agenta

Jeśli LLM ma zacząć pracę w c2004, najkrótsza sensowna ścieżka wygląda tak:

```bash
task tickets:next
task tickets:show -- PLF-XXX
task quality:regix:local
task monitor:probe
```

Najważniejsze dokumenty:

- [`../windsurf-agent-guide.md`](../windsurf-agent-guide.md)
- [`../../.windsurf/rules.md`](../../.windsurf/rules.md)
- [`../planfile-llm-guide.md`](../planfile-llm-guide.md)
- [`redsl/README.md`](./redsl/README.md) — jeśli ticket dotyczy
  OpenRouter automation lane lub `task quality:improve`

## Wzorzec README per tool

Każdy plik `README.md` w podfolderze ma 7 sekcji:

1. **Co to jest** — 1-zdaniowy opis
2. **Kiedy używać** — konkretne scenariusze
3. **Konfiguracja** — env vars, config plik, sample
4. **Komendy** — najczęściej używane
5. **Integracja z c2004** — gdzie jest podpięte (Taskfile, pre-commit, healing-webhook)
6. **Troubleshooting** — typowe problemy
7. **Linki** — repo, dokumentacja

## Aktualizacja modelu wszędzie

Patrz [`SESSION-2026-05-09-summary.md`](../SESSION-2026-05-09-summary.md)
sekcja 5b — w razie zmiany modelu domyślnego, edycja w 10 plikach:

```bash
# Quick check current model:
grep -h "^LLM_MODEL=" .env
grep "deepseek-v4-pro" .env .env.example */.\env* docker-compose.quality.yml \
     llx.yaml pyqual.yaml .aider/docker-compose.yml 2>/dev/null
```
