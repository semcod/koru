# LLM tools — index dla c2004

Każdy podfolder zawiera **README.md** (jak skonfigurować, kiedy używać) i
**install.sh** (idempotent, ~30 linii) dla pojedynczego narzędzia.

## Filozofia konfiguracji

c2004 używa pojedynczego env var `LLM_MODEL` jako **single source of truth**
dla domyślnego modelu (obecnie `openrouter/deepseek/deepseek-v4-pro`,
ustawione 2026-05-10 po empirycznym A/B teście — patrz
[`docs/SESSION-2026-05-09-summary.md`](../SESSION-2026-05-09-summary.md)).

Wszystkie narzędzia LLM-driven dziedziczą ten model przez:

- env var `LLM_MODEL` (lub specyficzny — `PFIX_MODEL`, `REFACTOR_LLM_MODEL`)
- config plik tool'a (`pyqual.yaml`, `redsl.yaml`, `llx.yaml`)

## Mapa narzędzi — według warstwy

```
WYKRYWANIE (LLM-free):              ROZWIĄZYWANIE (LLM):           WALIDACJA (LLM-free):
  regix     [regression]              llx       [model router]       ruff       [linter]
  redup     [duplicates]              pfix      [error fix]          pytest     [tests]
  prefact   [LLM-aware lint]          tillm     [shell clients]      regix      [regressions]
  testql    [declarative scenarios]   redsl     [quality gate +      vallm      [tier-1 syntax]
  planfile  [ticket store]                       improve]
  vallm/1   [syntax check]            windsurf  [primary IDE,
  sumd      [LLM snapshot for                    reuses agent LLM]
             LLM agents]
  op3       [multi-layer infra        redeploy  [markpact-based deploy:
             observation]                        detect → plan → apply]

ORCHESTRATION (LLM-free):
  goal      [smart commits + versioning + changelog + release workflow]
  doql      [declarative IaC: app.doql.less → build/sync/drift]
  costs     [AI cost tracker per commit (badge w README.md)]
  toonic    [TOON format converter (LLM-optimized compact YAML)]

SPECIALIZED (LLM-free):
  protogate [migration tool dla legacy systems (bounded slices)]
  rebuild   [code evolution intelligence (git history walker)]
  mdflow    [markdown dependency analyzer + Mermaid diagrams]
  metrun    [execution intelligence + bottleneck detection]

ON-CHANGE GATES TRIAD (LLM-free, continuous):
  wup       [semcod/wup: intelligent file/service watcher → priority/full testql probes]
            task quality:wup checks watcher config; wup watch runs the loop
  + regix     (delta gate, see WALIDACJA above)
  + testql    (HTTP probe, see WYKRYWANIE above)
  → koru brief surfaces all three in "On-change gates" section
  → /koru-gate slash command runs the triad on demand
  → see workflows/on-change-gates.md for the full cycle

  ALTERNATIVES:
    cursor       [IDE alternative to Windsurf]
    claude-code  [CLI agent alternative via semcod/tillm]
```

Shell LLM clients such as `aider` and `claude-code` are now documented and
controlled by the external `semcod/tillm` plugin. Koru keeps GUI/IDE and
pipeline docs here, while TILLM owns shell-client launch details.
Legacy client-specific workflows, including the old aider Docker autoloop,
also live in `semcod/tillm`.

## Ranking wymaganej konfiguracji

| Tool | Wymaga API key? | Specyficzna config? | Folder |
|---|---|---|---|
| **redsl** | ✅ OPENROUTER_API_KEY | ✅ `redsl.yaml` | [`redsl/`](./redsl/) |
| **llx** | ✅ OPENROUTER_API_KEY | ✅ `llx.yaml` (tiers) | [`llx/`](./llx/) |
| **pfix** | ✅ OPENROUTER_API_KEY | ✅ `PFIX_*` env | [`pfix/`](./pfix/) |
| **vallm** | optional (tier-2) | brak | [`vallm/`](./vallm/) |
| **prefact** | optional (autonomous) | ✅ `prefact.yaml` | [`prefact/`](./prefact/) |
| **planfile** | optional (init) | ✅ `planfile.yaml` | [`planfile/`](./planfile/) |
| **testql** | brak | ✅ scenariusze YAML | [`testql/`](./testql/) |
| **regix** | brak | ✅ `regix.yaml` | [`regix/`](./regix/) |
| **wup** | brak | ✅ `wup.yaml` (z koru template); opcjonalnie `testql-scenarios/` | [`wup/`](./wup/) |
| **redup** | brak | brak | [`redup/`](./redup/) |
| **sumd/sumr** | brak | brak (env vars) | [`sumd/`](./sumd/) |
| **redeploy** | brak | ✅ markpact specs (`*.md`) | [`redeploy/`](./redeploy/) |
| **goal** | optional (PYPI/NPM/GH tokens dla publish) | ✅ `goal.yaml` | [`goal/`](./goal/) |
| **doql** | brak | ✅ `app.doql.less` | [`doql/`](./doql/) |
| **costs** | brak | optional (`[tool.costs]` w pyproject.toml) | [`costs/`](./costs/) |
| **op3** | brak | brak (Pythonic API + CLI flags) | [`op3/`](./op3/) |
| **toonic** | brak | brak (CLI flags) | [`toonic/`](./toonic/) |
| **protogate** | brak | optional (`protogate.yaml`) | [`protogate/`](./protogate/) |
| **rebuild** | brak | optional (reads `pyqual.yaml`) | [`rebuild/`](./rebuild/) |
| **mdflow** | brak | brak (CLI flags) | [`mdflow/`](./mdflow/) |
| **metrun** | brak | brak (CLI flags) | [`metrun/`](./metrun/) |
| **windsurf** | (subskrypcja IDE) | ✅ `.windsurf/rules.md` | [`../windsurf-agent-guide.md`](../windsurf-agent-guide.md) |
| **cursor** | (subskrypcja IDE) | ✅ `.cursorrules` | [`cursor/`](./cursor/) |
| **shell LLM clients** | client-specific | client-specific | `semcod/tillm` |

## Quick install (wszystko)

```bash
# Z głównego katalogu c2004
for tool in redsl llx pfix vallm prefact planfile regix redup sumd redeploy goal doql costs op3 toonic protogate rebuild mdflow metrun testql; do
  bash docs/llm-tools/$tool/install.sh
done
pip install -e /home/tom/github/semcod/tillm
```

Każdy `install.sh` jest **idempotentny** — bezpiecznie uruchamiać wielokrotnie.

## Jak to jest używane w c2004

Te narzędzia nie są w repo "obok siebie". One tworzą wspólny workflow z
dwoma trybami:

- **Default path** — ticket-driven development z agentem IDE
  (Windsurf/Cursor/Claude Code), bez zdalnych wywołań LLM.
- **Opt-in automation lane** — narzędzia LLM-backed (`redsl improve`,
  `llx`, shell clients through `tillm`) do smoke-testów, jakościowej infrastruktury i
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

### Koru jako kontroler semcod/* → planfile

W repo zarządzanym przez Koru standardowa komenda operatorska to:

```bash
task install:tools
task quality:semcod:planfile
```

`quality:semcod:planfile` uruchamia tylko realnie dostępne i skonfigurowane
bramki, a każdą awarię zapisuje jako deduplikowany ticket w `planfile`:

- `koru scan --apply --semcod-artifacts` — tickety z realnych sygnałów repo;
- `regix gates` — regresje metryk;
- `wup status` — stan watchera plików/usług;
- `testql suite ...` — awarie scenariuszy HTTP/API;
- `redup scan ...` — przekroczone progi duplikacji;
- `scripts/sumr-refresh.sh --status` — nieświeże snapshoty SUMR/SUMD;
- `doql check app.doql.less` i `redsl gate check .`, gdy są skonfigurowane.

Każdy ticket dostaje znacznik `[gate-finding:<hash>]`, więc ponowny przebieg
nie produkuje duplikatów; przy `UPDATE_EXISTING=1` dopisuje notatkę do
istniejącego zgłoszenia. Do bezpiecznego sprawdzenia użyj:

```bash
DRY_RUN=1 task quality:semcod:planfile
```

### Autonomiczna strategia przy pustej kolejce

Gdy `koru auto` / `koru autonomous up` kończy cykl z pustą kolejką
(`last_status=idle`), może przejść z realizacji lokalnych ticketów do szerokiego
odkrywania pracy w całym projekcie. Warunkiem jest aktywne skanowanie po idle i
artefakty semcod. `koru auto` włącza `--scan-after-idle-queue` domyślnie, żeby
cykl przechodzący z `waiting_input` do `idle` od razu uruchamiał intake
discovery; można to wyłączyć przez `--no-scan-after-idle-queue`. Dla `koru
autonomous up` włącz te ustawienia jawnie albo użyj trybu adaptacyjnego
`KORU_AUTO_PIPELINE=1`, który robi to dla etapów quality i architecture:

```bash
koru autonomous up \
  --ticket-sources queue \
  --scan-after-idle-queue \
  --scan-after-idle-min-interval 60 \
  --semcod-artifacts
```

Kolejność działania jest celowo deterministyczna:

1. Koru uruchamia `koru scan --apply --semcod-artifacts` jako tani intake scan.
2. Jeżeli scan nie doda nowych ticketów, Koru uruchamia lokalnie `code2llm`:

  ```bash
  code2llm "$PROJECT" \
    -f all \
    -o "$PROJECT/project" \
    --no-chunk \
    --exclude '*.md' \
    --planfile-apply \
    --planfile-source koru-project-discovery \
    --planfile-sprint current \
    --planfile-project "$PROJECT" \
    --planfile-limit 20
  ```

3. `code2llm` odświeża `project/analysis.toon.yaml`, mapy projektu i
  `project/planfile-tickets.yaml`, a następnie aplikuje maksymalnie 20
  deduplikowanych ticketów przez `planfile`.
4. Nowe zgłoszenia trafiają do normalnej kolejki `planfile`; agent wraca do
  pracy ticket po tickecie zamiast wykonywać szeroki refactor bez zadania.
5. Koru emituje `Code2llmDiscoveryCompleted` z polami `ran`, `applied`,
  `skipped` i `error`, więc przebieg jest widoczny w logach/JSONL.

Pełny przebieg `code2llm` jest pomijany, gdy `project/analysis.toon.yaml` jest
młodszy niż 60 minut; `--scan-after-idle-min-interval` ogranicza też częstotliwość
intake scanów po idle. Jeżeli `code2llm` nie jest dostępny na `PATH` albo kończy
się błędem, Koru zapisuje wynik jako skipped/error i nie wstrzykuje ogólnego
promptu do IDE. Po instalacji `code2llm` można ponowić cykl albo uruchomić
powyższą komendę ręcznie.

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
     llx.yaml pyqual.yaml 2>/dev/null
```
