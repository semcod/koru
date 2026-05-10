# LLM Agent Guide — koru-driven repositories

> **Audience:** LLM agent (Windsurf, Cursor, Claude Code, aider). Read this
> document before the first session in any **koru-driven repository**.
>
> **TL;DR:** use `task tickets:next` as the entry point, edit code, validate
> with `task quality:regix:local` + pytest, commit. **By default**, do NOT
> invoke remote LLM APIs (`redsl improve`, `llx fix`, `aider`) — koru repos
> use **your** LLM (the IDE's, e.g. Windsurf). The OpenRouter path exists as
> an **opt-in automation lane** for infrastructure tests and headless
> auto-fixes.
>
> **Reference deployment:** This guide was originally written for
> [`maskservice/c2004`](https://github.com/maskservice/c2004). Sections
> mentioning `c2004` apply to any koru-aligned repo with equivalent
> infrastructure (`Taskfile.yml`, `pyqual.yaml`, `planfile`, `redup`, `regix`).

---

## 1. Filozofia — kto za co odpowiada

```
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  WYKRYWANIE          │  │  AGENT (TY)          │  │  WALIDACJA           │
│  (LLM-free, server)  │  │  (LLM Windsurfa)     │  │  (LLM-free, lokalne) │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ • Prometheus alerts  │  │ • czytasz tickety    │  │ • ruff               │
│ • testql probes      │─→│ • edytujesz kod      │─→│ • redsl gate         │
│ • healing-webhook    │  │ • piszesz testy      │  │ • regix              │
│ • planfile tickets   │  │ • commit             │  │ • pytest             │
│ • vallm pre-flight   │  │                      │  │ • testql probes      │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
       Tworzy backlog          Generuje patch          Zatwierdza patch
```

**Twoja rola:** middle column. Dwie strony są zaautomatyzowane i nigdy nie
proszą cię o ręczne uruchomienie. Po prostu czytasz i piszesz kod.

---

## 2. Toolchain — co jest zainstalowane

### 2.1. Narzędzia oparte na regułach (LLM-free)

Używaj ich agresywnie do self-verification — nie kosztują tokenów.

| Tool | Komenda | Co robi |
|---|---|---|
| **regix** | `task quality:regix:local` | Porównuje metryki (CC, MI, coverage, length, docstring) między working tree a HEAD. Wykrywa regresje przed commitem. |
| **redsl** | `task quality:gate` | Sprawdza absolute thresholds (max CC, max function length, forbidden patterns). |
| **vallm** | `vallm check --file <path>` | Tier-1 syntax check (~50ms/plik). Tier-2 z LLM-as-judge dostępne ale unikaj — używasz swojego LLM. |
| **redup** | `task quality:redup` lub MCP tool | Wykrywa duplikaty kodu w monorepo (50+ connect-* modułów). |
| **testql** | `task monitor:probe` | Uruchamia 50 deklaratywnych assertions na endpointach API/UI. |
| **prefact** | `prefact check .` | LLM-aware linter — sprawdza struktury które LLM często psuje (unused imports nieprawdziwie wstawione, nieukończone funkcje, etc.). |
| **planfile** | `task tickets:next` / MCP | Backlog ticketów stworzonych przez healing-webhook. |
| **ruff** | `pre-commit run --all-files` | Linter + formatter. |
| **pytest** | `task test` | Test suite. |

### 2.2. MCP servers (jeśli wpisane w `~/.codeium/windsurf/mcp_config.json`)

Jeśli user dodał wpisy z `.windsurf/mcp_config.example.json`, masz natywny
dostęp przez MCP — wywołuj jak inne tools, **bez subprocess**:

| MCP server | Tools |
|---|---|
| `planfile` | `ticket_list`, `ticket_show`, `ticket_create`, `ticket_update` |
| `testql` | `scenario_run`, `scenario_list`, `last_results` |
| `redup` | `analyze_project`, `find_duplicates`, `suggest_refactoring`, `compare_scans` |

Jeśli MCP nie skonfigurowane — używaj CLI (`planfile ticket show ...`).

### 2.3. Dwa tryby pracy

| Tryb | Kiedy | Co robisz |
|---|---|---|
| **Default: IDE-native** | zwykła praca nad ticketem, refaktor, bugfix, regresja | `task tickets:next` → edycja kodu → `regix` / `pytest` / `testql` |
| **Opt-in: OpenRouter automation lane** | tylko gdy user explicite testuje automatyzację refaktoryzacji, `healing-webhook`, `task quality:improve` albo smoke-test ścieżki server-side | wolno uruchomić `redsl improve` lub pokrewne narzędzia, ale traktuj to jako test infrastruktury, nie domyślny workflow |

### 2.4. Narzędzia których domyślnie NIE używaj

| Tool | Dlaczego nie |
|---|---|
| `redsl improve` | Domyślny workflow nie potrzebuje OpenRouter. Używaj tylko w opt-in automation lane lub przy jawnej prośbie usera. |
| `llx fix` | Jak wyżej. |
| `aider` | Jak wyżej. |
| `vallm validate` (tier-2) | Wywołuje LLM-as-judge → kosztuje. Używaj tylko gdy ticket dotyczy walidacji ścieżki LLM-backed. |
| `requests.get(<public URL>)` | Brak kontroli, nie rób network calls. |

---

## 3. Standardowy workflow

### 3.1. Entry point — co robić "co dalej"

```bash
task tickets:next
```

Wynik: `Highest-priority ticket: PLF-XXX` plus pełny markdown.

### 3.2. Struktura ticketu (zawsze tej samej)

Ticket ma 7 sekcji:

```markdown
## 🚨 Context              ← alert, severity, component, commit SHA
## 🔁 Reproduction         ← bash commands do skopiowania
## 📂 Likely-affected areas ← lista plików/glob patterns
## 🔍 vallm pre-flight     ← syntax score per-plik (auto-dodawane)
## ✅ Acceptance criteria  ← checkboxy
## 🔒 Constraints          ← czego NIE wolno
## 🤖 Prompt               ← gotowy dla agenta (czyli ciebie)
## 📎 Raw alert payload    ← oryginalny JSON
```

### 3.3. Kroki naprawy (checklist)

1. **Read ticket** — `task tickets:show -- PLF-XXX` lub MCP `ticket_show`.
2. **Read affected files** — pliki z sekcji "📂 Likely-affected areas".
3. **Reproduce** — uruchom bash z "🔁 Reproduction" jeśli możliwe (czasem
   wymaga external service który leży — odnotuj to userowi).
4. **Identify root cause** — przed pisaniem kodu, opisz w 1-2 zdaniach co
   jest nie tak. Jeśli niepewne, czytaj więcej plików, nie zgaduj.
5. **Plan minimal patch** — ≤ 80 linii diff, jeden problem na ticket.
6. **Edit** — używaj edit/multi_edit. Nie pisz nowych plików chyba że
   konieczne.
7. **Self-validate**:
   ```bash
   task quality:regix:local           # 0 errors required
   bash scripts/regix-precommit.sh    # to samo via pre-commit
   pytest <affected_module> -q        # punktowy test
   ```
8. **Add regression test** — który by złapał ten bug. Bez wyjątków.
9. **Commit** — pre-commit auto-uruchomi: ruff, redsl-gate, regix.
10. **Mark done** — `task tickets:done -- PLF-XXX`.

### 3.4. Kiedy zatrzymać i zapytać usera

Zatrzymaj się i zapytaj jeśli:

- Patch przekracza 80 linii diff → prawdopodobnie ticket trzeba podzielić.
- Trzeba dotknąć pliku spoza "Likely-affected areas".
- Trzeba bumpać dependency (`requirements*.txt`).
- Trzeba dodać nowy connect-* moduł / nowy top-level dir.
- Test trzeba zdisable'ować (nawet czasowo).
- Reprodukcja zawodzi z niejasnych powodów (3+ próby).
- Nie jesteś pewny intencji ticketu w 80% — nie zgaduj.

Nie pytaj o:

- Type hints, docstrings, rename lokalnych zmiennych.
- Dodanie testu regresji.
- Uruchomienie task / pytest / regix do verify.
- Drobne refaktory w skali metody.

### 3.5. Jak interpretować czerwone komendy

Nie każda czerwona komenda oznacza ten sam typ problemu. Rozróżniaj:

| Komenda | Najczęściej oznacza | Domyślna reakcja |
|---|---|---|
| `task test` | bug produktu, drift wersji, import/runtime error | sprawdź backlog, odtwórz lokalnie, napraw kod lub artefakt |
| `task monitor:probe` | runtime regression serwisu lub endpointu | zawęź do konkretnego portu/endpointu, potem pracuj z ticketem |
| `task quality:regix:local` | twój aktualny diff pogorszył metryki | popraw patch zanim ruszysz dalej |
| `task quality:redup:check` | nowa duplikacja lub zły kierunek migracji | wyciągnij reusable kod do `packages/` albo `shared/` |
| `task quality:improve` | quality-stack / OpenRouter lane problem | traktuj jak ticket infrastrukturalny, nie jak bug domenowy |
| `task monitor:test-heal` | observability/healing-webhook problem | sprawdź `healthz`, logi webhooka i compose wiring |

Reguła:

- **produkt**: endpointy, domena, testy funkcjonalne,
- **infrastruktura refaktoryzacji**: `quality:*`, `monitor:test-heal`, compose quality stack,
- **twój diff**: `regix`, `redup`, pre-commit gates.

---

## 4. Konwencje kodu c2004

### 4.1. Struktura repo

```
backend/                 ← główny FastAPI service (port 8101)
backend/app/             ← business logic
backend/api/routes/      ← REST endpoints (v1, v2, v3)
backend/firmware/        ← embedded code (RP2040 + RPi4)

connect-*/               ← per-domain microservices (DOMAIN-SPECIFIC code)
  ├── backend/           ← FastAPI subserwis
  ├── frontend/          ← Vue 3 / React komponenty (zależnie od modułu)
  └── tests/             ← lokalne testy

frontend/                ← główny Vue 3 SPA (port 8100)

packages/                ← FORMAL PIP/NPM packages z pyproject.toml/package.json
  ├── backend-shared-py/ ← `c2004-backend-shared` (canonical Pydantic models, DB)
  ├── contracts-types/   ← TS contracts
  ├── ts-utils/          ← TS utils
  └── ui-components/     ← Vue components

shared/                  ← COMPATIBILITY SHIM LAYER (NOT canonical impl!)
                           Re-exports z `packages/backend-shared-py/src/shared/`
                           przez `extend_shared_path()` + bootloader wrappers.
                           Symlinks do `frontend/src/{components,core,modules,...}`.

services/                ← niezależne mikroserwisy (Tic249, modbus-io, ...)

monitoring/              ← Prometheus, Grafana, healing-webhook, testql-watchdog
testql-testing/          ← deklaratywne scenariusze testów

planfile.yaml            ← backlog (auto-zarządzany przez healing-webhook)
regix.yaml               ← regression detection thresholds
redsl.yaml               ← refactor + quality gates
prefact.yaml             ← LLM-aware linter
pyqual.yaml              ← pipeline orchestration
```

### 4.1.1. Kierunki migracji kodu (ARCHITECTURAL RULE)

Gdy edytujesz kod, kieruj się tymi zasadami umiejscowienia:

| Co to jest | Gdzie powinno być | Przykład |
|---|---|---|
| **Reużywalne między ≥2 modułami** (`frontend`+`backend`, lub ≥2 connect-*) | `packages/` (formal package z pyproject) | `c2004-backend-shared`, `ui-components` |
| **Reużywalne, ale nie wymaga formalnego packagu** | `shared/` (compat shim, top-level) | `shared/protocol_models.py` (bootloader → canonical) |
| **Specyficzne dla jednego connect-\*** | `connect-XXX/backend/` lub `connect-XXX/frontend/` | `connect-data/backend/.../events.py` (tylko dla connect-data) |
| **Specyficzne dla głównego `backend/`** | `backend/app/` | `backend/app/api/routes/v3/*.py` |

**Decyzja "duplicate vs specific" dla redup findings:**

- Jeśli ten sam kod jest w `shared/` ORAZ `packages/backend-shared-py/`: prawie zawsze
  shim w `shared/` (sprawdź: `head -5 <plik>` powinien mieć `Compatibility wrapper for`).
  `redup-check.sh` ma `is_compat_shim()` filter który automatycznie pomija takie pliki.
- Jeśli ten sam kod jest w 2+ `connect-*/`: zdecyduj — przenieś do `packages/` lub
  zachowaj template-based copies (np. CQRS handlers z connect-template).
- Jeśli ten sam kod jest w `connect-X/` i `packages/backend-shared-py/`: usuń z connect-X
  (canonical wins) i importuj z `from shared.X import …`.

**NIE pisz nowego kodu w `shared/`** — pisz w `packages/backend-shared-py/src/shared/`,
a w `shared/` ewentualnie dodaj compat wrapper jeśli potrzebny dla legacy importów.

### 4.1.2. Standard pattern shim'a (canonical → re-export)

Gdy tworzysz lub upraszczasz compatibility wrapper dla modułu z `packages/`,
**używaj kanonicznego patternu** (najmniejszy boilerplate, automatyczna spójność
z `__all__` canonical):

```python
"""Compatibility wrapper for <nazwa>.

Canonical implementation lives in:
`packages/backend-shared-py/src/shared/<path>`
"""

from __future__ import annotations

from shared._compat import export_backend_shared_module

__all__ = export_backend_shared_module(globals(), "<path>")
```

Reference implementations (audit 2026-05-10):
- `shared/types/base.py` (307B) — minimal pattern
- `shared/types/__init__.py` (535B) — package-level shim
- `backend/app/domain/live_protocol/events.py` (486B)
- `backend/app/cqrs/live_protocol/events.py` (484B)

**NIE pisz** explicit `getattr(_module, "Foo")` + manualne `__all__ = [...]`
listy — `export_backend_shared_module` robi to automatycznie używając
canonical's `__all__` lub heurystyki (publiczne symbols).

**Kiedy NIE używać tego pattern:**
- Gdy wymagany jest **graceful fallback do stub** (Docker bez packages/)
  — wtedy własny bootloader, np. `shared/menu_models.py`, `backend/app/domain/testing/events.py`
- Gdy moduł canonical jest w `connect-*/`, NIE w `packages/` — wtedy używaj
  `app.connect_compat.export_connect_module()` (np. `backend/app/domain/device/events.py`)

### 4.2. Style

- **Python:** Python 3.12, Pydantic v2, FastAPI, async/await dla I/O.
  Type hints zawsze. Docstrings dla public API.
- **JavaScript/TypeScript:** Vue 3 Composition API w głównym frontend,
  React/Tailwind w niektórych connect-* (sprawdź sąsiednie pliki).
- **Imports:** zawsze na górze pliku. Nigdy w środku funkcji.
- **Functions:** ≤ 100 linii (regix `length_max=100`).
- **Cyclomatic complexity:** ≤ 15 per funkcja (regix `cc_max=15`).
- **Error handling:** używaj logging.exception, nie print.

### 4.3. Testy

- Lokalizacja: `<module>/tests/` lub `tests/<module>/`.
- Naming: `test_*.py`, klasy `Test*`, funkcje `test_*`.
- Fixtures: pytest fixtures w `conftest.py`.
- Coverage threshold: `coverage_min: 50` (regix.yaml). Dążymy do 80%.
- Każdy bug fix → regression test. Bez wyjątków.

### 4.4. Commits

- Convention: `<type>(<scope>): <subject>`.
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
- Subject: tryb rozkazujący po angielsku, ≤ 72 znaki.
- Body opcjonalny: opisz co i dlaczego (nie jak).
- Pre-commit hooki uruchamiane automatycznie.

---

## 5. Cytowanie plików w odpowiedziach

Używaj zawsze absolute paths w formacie:

```
@/home/tom/github/maskservice/c2004/backend/app.py:42-48
@/home/tom/github/maskservice/c2004/connect-scenario/backend/...:30
```

Nigdy plain text paths typu `backend/app.py:42`.

---

## 6. Cheat-sheet komend (najczęściej używane)

```bash
# === Backlog ===
task tickets:next                  # kolejny ticket do zrobienia
task tickets:list                  # wszystkie open
task tickets:show -- PLF-021       # konkretny ticket
task tickets:done -- PLF-021       # zamknij po commit
task tickets:webhook:created       # tylko z healing-webhook

# === Quality (LLM-free, używaj zawsze) ===
task quality:regix:local           # regresje vs HEAD
task quality:regix:branch          # regresje branch vs main
task quality:regix:report          # JSON+TOON do .regix/
task quality:gate                  # absolute thresholds (redsl)
task quality:health                # snapshot zdrowia repo

# === Tests ===
task test                          # full suite
pytest backend/tests/<file>.py -q  # punktowy
task monitor:probe                 # 50 endpointów assertions

# === Discovery (kiedy nie wiesz gdzie ===
task quality:redup                 # duplikaty
prefact check backend/             # LLM-aware lint
git log --oneline -20              # ostatnie commity
```

---

## 7. Anti-patterns (czerwone flagi)

❌ **Nie commituj zanim nie:**
- Uruchomisz `task quality:regix:local` (musi być 0 errors)
- Dodasz regression test
- Sprawdzisz `git status` → tylko zamierzone pliki

❌ **Nie używaj `--no-verify`** żeby ominąć pre-commit. Lepiej napraw
przyczynę.

❌ **Nie wywołuj `redsl improve` / `llx fix`** w zwykłym ticket flow.
To wolno tylko wtedy, gdy user explicite testuje OpenRouter lane albo
naprawiasz infrastrukturę headless auto-refactor.

❌ **Nie modyfikuj generated code:** `**/*_pb2*.py`, `**/__generated__/**`,
`archive/**`, `_archive/**`.

❌ **Nie dodawaj `print()` w produkcyjnym kodzie** — używaj `logging`.

❌ **Nie zgaduj importów** — szukaj prawdziwego symbolu w sąsiednich
plikach.

❌ **Nie pisz "tymczasowych" workaroundów** — fix przyczynę albo zostaw
ticket w stanie open i zaznacz blocker.

---

## 8. Co robić jak healing-webhook NIE działa

Jeśli `task tickets:next` zwraca "No open tickets" ale są realne problemy:

1. Sprawdź czy stack monitoringu chodzi: `task quality:status`.
2. Sprawdź `docker logs c2004-healing-webhook --tail 50`.
3. Manualnie wystartuj: `task monitor:up`.
4. Jeśli to bug w samym webhooku — utwórz ticket przez `planfile ticket
   create` z opisem.

---

## 9. Dalsza lektura

- `@/home/tom/github/maskservice/c2004/.windsurf/rules.md` — krótkie reguły, auto-loaded
- `@/home/tom/github/maskservice/c2004/README.md` — overview repo + monitoring stack
- `@/home/tom/github/maskservice/c2004/docs/planfile-llm-guide.md` — szczegóły ticketów LLM-ready
- `@/home/tom/github/maskservice/c2004/regix.yaml` — thresholds regresji (komentarze tłumaczą każde pole)
- `@/home/tom/github/maskservice/c2004/redsl.yaml` — quality gates
- `@/home/tom/github/maskservice/c2004/.windsurf/workflows/` — wieloetapowe procedury

---

## 10. Najczęstsze typy ticketów i jak je rozwiązywać

### 10.1. `EndpointDown` (alert Prometheus)

- **Symptom:** `curl <endpoint>` → 5xx lub timeout.
- **Lookup:** sekcja "Likely-affected areas" wskaże routes/handlers.
- **Typical fix:** brakująca DB connection, race condition w lifespan,
  niezarejestrowany router. Sprawdź `docker logs <service>`.

### 10.2. `[TestQL] BROKEN button` (UI audit)

- **Symptom:** przycisk w UI nie reaguje lub rzuca błąd JS.
- **Lookup:** selektor CSS w ticket → grep w `frontend/` lub
  `connect-*/frontend/`.
- **Typical fix:** event handler nie podpięty, niezdefiniowana funkcja,
  złe API endpoint URL.

### 10.3. `RegressionDetected` (regix)

- **Symptom:** CC/MI/length przekroczyły threshold.
- **Lookup:** raport regix wskazuje konkretną funkcję.
- **Typical fix:** wyodrębnij sub-funkcje, usuń duplikację, simplify
  warunki.

### 10.4. `DuplicateCode` (redup)

- **Symptom:** 2+ funkcje z identyczną logiką w różnych modułach lub ticket
  z labelem `redup-detected`.
- **Lookup:**
  - `task quality:redup:report` — generuje `.redup/check.filtered.json` (po
    wykluczeniach z `redup.toml` + shim filter w `redup-check.sh`)
  - Top groups: `python3 -c "import json; d=json.load(open('.redup/check.filtered.json')); [print(g) for g in d['groups'][:5]]"`
  - Pyqual stage `duplicate-check` (advisory) uruchamia ten sam skrypt.
- **Typical fix:** wyciągnij do `packages/backend-shared-py/src/shared/`
  zgodnie z migration direction (sekcja 4.1.1).
- **Budżet duplikatów (redup.toml):** `max_groups=400`, `max_lines=6000`. Po
  filtrze baseline ~25 grup. Healing-webhook tworzy ticket z label
  `redup-detected` gdy budżet przekroczony.
- **Metryki Prometheus:**
  - `c2004_redup_groups` — liczba grup po filtrze
  - `c2004_redup_saved_lines` — sumaryczne linie do odzyskania
  - `c2004_redup_budget_breach` — 1 jeśli budżet przekroczony
- **TypeScript:** redup obsługuje **TYLKO Python**. Frontend duplicate
  detection (TS/JSX) przez jscpd jest planowany — patrz ticket PLF-057.

### 10.5. `LowCoverage` (pytest-cov)

- **Symptom:** module coverage < 50%.
- **Lookup:** `task quality:health` lub `.pyqual/coverage.json`.
- **Typical fix:** dodaj testy edge-case'ów. Nie pisz testów które tylko
  wywołują kod — testuj zachowanie i błędy.

---

**Gdy w wątpliwości:** preferuj akcję która jest LLM-free, łatwa do
revertu (jeden mały commit), dodaje test. Repo nagradza precyzję, nie
prędkość.
