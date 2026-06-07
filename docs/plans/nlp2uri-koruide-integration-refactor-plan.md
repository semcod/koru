# Plan refaktoryzacji — integracja nlp2uri z kontrolą IDE Koru

**Status:** proposed  
**Data:** 2026-06-07  
**Właściciel:** Koru + nlp2uri (cross-repo)  
**Baseline:** [ide-control-architecture.md](../ide-control-architecture.md)

## Cel

Rozdzielić warstwy tak, aby:

1. **Koru (`koruide`)** pozostał **jedynym wykonawcą** live IDE automation (daemon, plugin, ack, fallbacki).
2. **`nlp2uri`** stał się **warstwą adresowania i planowania**: NL → URI → `koru.control.v1` → delegacja do Koru.
3. Agenci (MCP, autonomous, zewnętrzne LLM) mogły **planować i replayować** sterowanie IDE bez duplikowania logiki probe/pluginów.

## Nienaruszalne zasady

| Zasada | Uzasadnienie |
|--------|--------------|
| Nie przenosić probe-ladder do `nlp2uri` | Runtime, zależny od wersji pluginu i IDE |
| Nie przenosić keyboard fallback / OS strategy | Wayland/X11, focus guards — już w Koru/gillm |
| Tekst promptu **nie w path URI** | Bezpieczeństwo, długość, replay w body planu |
| `require_plugin` egzekwowane przez Koru | `nlp2uri` tylko ustawia flagę w planie |
| Sukces ≠ exit code | Wymaga ack / `message.sent` / verification metadata |

## Zakres

### W zakresie

- Nowe schematy URI w `nlp2uri` (`ide`, `ide_chat`, `ide_command`, `koru_control`)
- Model `ControlAction` / `ExecutionPlan` kompilowany do `koru.control.v1`
- Driver Koru w `nlp2uri` (dry-run + execute)
- Parser NL dla intencji IDE (PL + EN)
- SystemMap ingest stanu Koru (status, pluginy, workspaces)
- MCP tools i TestQL round-trip
- Dokumentacja i cross-linki (Koru + nlp2uri SUMD)

### Poza zakresem (Koru only)

- Refactor `handlers_drive.py` / probe-ladder (osobny plan KIDE)
- Ekstrakcja `koruide` do osobnego pakietu PyPI (ADR KIDE-001)
- Naprawa focusu Cursor/Glass na Wayland
- Zmiana protokołu plugin v2 → v3

---

## Fazy implementacji

### Faza 0 — Dokumentacja i kontrakty ✅

**Repo:** Koru  
**Deliverables:**

- [x] `docs/ide-control-architecture.md` — analiza stanu obecnego
- [x] `docs/plans/nlp2uri-koruide-integration-refactor-plan.md` — ten plan
- [x] Cross-linki w `docs/README.md`, `desktop-uri-orchestration.md`
- [x] Sekcja w `nlp2uri/SUMD.md` (sibling) — baseline integracji

**Kryterium akceptacji:** Agent może przeczytać docs i wiedzieć, która warstwa co robi.

---

### Faza 1 — Registry i URI builders (nlp2uri) ✅

**Repo:** `nlp2uri`  
**Status:** done (2026-06-07)

#### Zadania

1. Rozszerzyć `schemas/registry.yaml`:

   ```yaml
   ide:
     layer: control
     uri_pattern: "ide://{ide}/{action}"
   ide_chat:
     layer: control
     uri_pattern: "ide-chat://{ide}/{action}"
   ide_command:
     layer: control
     uri_pattern: "ide-command://{ide}/{action}"
   koru_control:
     layer: control
     uri_pattern: "koru-control://{surface}/{operation}"
   ```

2. Dodać buildery URI (np. `nlp2uri/uri_builders/ide.py`):
   - `build_ide_open(ide, workspace, file?, line?)`
   - `build_ide_chat_send(ide, workspace, submit, require_plugin?)`
   - `build_koru_control_drive(ide, workspace, ...)`

3. Rozszerzyć `IntentKind` w `models.py`:

   ```python
   IDE_OPEN = "ide_open"
   IDE_CHAT_SEND = "ide_chat_send"
   IDE_COMMAND = "ide_command"
   IDE_STATUS = "ide_status"
   KORU_CONTROL = "koru_control"
   ```

4. Testy jednostkowe: round-trip builder → parse URI → slots.

**Kryterium akceptacji:** `nlp2uri plan "ide-chat://cursor/send?workspace=/path&submit=true"` zwraca plan z `kind=control` (nawet jeśli execute jeszcze nie działa).

**Zrealizowane pliki:** `schemas/registry.yaml`, `schemes/ide/v1/*`, `schemes/ide_chat/v1/*`, `schemes/ide_command/v1/*`, `schemes/koru_control/v1/*`, `src/nlp2uri/schemes/ide.py`, `parse_nl.py` (IDE_CHAT_SEND, IDE_STATUS), `tests/test_ide_control.py`.

---

### Faza 2 — ControlAction i kompilacja do koru.control.v1 (nlp2uri) ✅

**Repo:** `nlp2uri`  
**Status:** done (2026-06-07)  
**Zależność:** Faza 1

#### Zadania

1. Nowy model `ControlAction` / `ControlPlan` obok `OSAction`:

   ```yaml
   kind: control
   command_version: koru.control.v1
   surface: ide_chat
   transport: koruide_socket
   operation: drive
   args:
     ide: cursor
     workspace: /abs/path
     submit: true
     require_plugin: false
     strategy_hint: auto
   text_ref: plan_body   # tekst poza URI
   verification:
     expect_ack: true
     expect_message_sent: true
     timeout_ms: 120000
   replay:
     cli: "koru autopilot drive --ide cursor --require-plugin ..."
     mcp_tool: koru_ide_drive
   ```

2. `compile.py` — gałąź `compile_control_uri()` dla schematów `ide_*`, `koru_control`.
3. Dry-run **nigdy** nie wysyła tekstu do IDE — tylko zwraca plan + replay descriptor.
4. Testy: compile → JSON schema validation vs `koru.control.v1` (Koru może udostępnić JSON Schema w docs).

**Kryterium akceptacji:** TestQL / pytest: `compile_uri_to_actions("ide-chat://cursor/send?...")` → `transport=koruide_socket`, `operation=drive`.

**Zrealizowane pliki:** `src/nlp2uri/models.py` (`ControlAction`, `ControlPlan`, `ControlVerification`), `src/nlp2uri/control_compile.py`, `resolve.py` (attach `control_plan`), `NLP2URIResult.to_dict()`.

---

### Faza 3 — Driver Koru w nlp2uri (execute) ✅

**Status:** done (2026-06-07)

**Repo:** `nlp2uri`  
**Szacunek:** 2–4 dni  
**Zależność:** Faza 2

#### Zadania

1. Adapter `nlp2uri/adapters/koru.py`:
   - **dry_run:** zwraca `ControlPlan` (domyślnie)
   - **execute:** opcjonalnie, `KORU_IDE_CONTROL_EXECUTE=1` lub flaga CLI `--execute`

2. Ścieżki wykonania (kolejność preferencji):
   - Import `koruide.client.KoruIDEClient` (jeśli Koru zainstalowany editable)
   - MCP subprocess `koru_ide_drive` (nowe narzędzie w Koru MCP — Faza 4)
   - CLI fallback: `koru autopilot drive ...`

3. Mapowanie wyniku:
   - `ack.ok` → `status=acknowledged`
   - timeout → `status=verification_failed`, `reason=ack_timeout`
   - `require_plugin` + brak pluginu → `status=blocked`, nie generic error

4. Zależność opcjonalna: `nlp2uri[koru]` extra w `pyproject.toml`.

**Kryterium akceptacji:** `nlp2uri handle "ide-chat://cursor/send?..." --text-file prompt.txt --dry-run` + mocked execute w testach.

**Zrealizowane pliki:** `src/nlp2uri/control_execute.py` (koruide socket + CLI fallback), `tests/test_koru_control_execute.py`.

---

### Faza 4 — MCP i most Koru (Koru + nlp2uri) ✅

**Status:** done (2026-06-07)  
**Zależność:** Faza 2–3

#### Zadania Koru

1. Narzędzia MCP (`mcp_server_ide.py`):
   - [x] `koru_ide_drive` — wrap `AutopilotClient.drive`
   - [x] `koru_ide_commands` / catalog — status i telemetry
   - [x] `koru_ide_control_plan` — NL → `koru.control.v1` plan
   - [x] `koru_ide_control_execute` — plan + execute (dry-run domyślnie)

2. [x] `desktop_uri_plan` / `desktop_uri_control_plan` / `desktop_uri_control_execute`

3. [x] `KORU_IDE_CONTROL_VIA_NLP2URI=1` → `try_nlp2uri_ide_control()` w `autonomous_cycle_gate.py`

#### Zadania nlp2uri

1. Rozszerzyć `nlp2uri-mcp` o `compile_control_uri`, `execute_control_plan`.
2. Dokumentacja w `nlp2uri` README + SUMD.

**Kryterium akceptacji:** Agent MCP może: plan NL → `ide-chat://...` → dry-run → `koru_ide_drive` z tym samym body.

---

### Faza 5 — Parser NL (nlp2uri) ✅

**Status:** done (2026-06-07) — `IDE_CHAT_SEND`, `IDE_STATUS`, `IDE_COMMAND` (EN+PL)  
**Zależność:** Faza 1

#### Przykłady do obsługi

| NL (PL/EN) | Intent | URI |
|------------|--------|-----|
| wyślij prompt do Cursor w tym projekcie | `IDE_CHAT_SEND` | `ide-chat://cursor/send?workspace=...` |
| wklej do Windsurf, ale nie wysyłaj | `IDE_CHAT_SEND` | `submit=false` |
| użyj tylko pluginu, bez klawiatury | `IDE_CHAT_SEND` | `require_plugin=true` |
| sprawdź status pluginu IDE | `IDE_STATUS` | `koru-control://ide/status` |
| otwórz cursor z projektem /path | `IDE_OPEN` | już częściowo w `parse_nl.py` |

Implementacja: regex + slot filling (jak dziś), później opcjonalnie LLM slot fill przez `nlp2cmd` bridge (`NLP2CMD_INTEGRATION=1` — wzorzec z `desktop_uri.py`).

**Kryterium akceptacji:** TestQL scenariusze PL+EN z fixture prompts.

---

### Faza 6 — SystemMap ingest (nlp2uri + Koru) ✅

**Status:** done (2026-06-07)  
**Zależność:** Faza 4

#### Zadania

1. [x] Koru: `koru autopilot status --format systemmap` (`ide_status_systemmap.py`).
2. [x] nlp2uri: `systemmap/koru_ide.py` — indeks URI:
   - `ide://cursor`
   - `ide://cursor/workspace/{encoded-path}`
   - `koru-control://plugin/{session-id}`
   - `ide-command://cursor/execute?command=...` (z `commandCatalog` w hello)

3. `koru_env2llm_list_uris` — pokazuje encje IDE obok desktop/getv.

**Kryterium akceptacji:** Po `Connect autopilot daemon` indeks zawiera plugin + workspace dla aktywnego IDE.

---

### Faza 7 — TestQL i CI ✅

**Status:** done (2026-06-07)  
**Zależność:** Fazy 1–6

#### Scenariusze

1. `parse_text("wyślij prompt do Cursor")` → `IDE_CHAT_SEND`
2. `build_uri` → `ide-chat://cursor/send?...`
3. `compile` → `koru.control.v1` z `transport=koruide_socket`
4. Dry-run nie dotyka socketu
5. Mocked `KoruIDEClient.drive` → ack mapping
6. `require_plugin=true` + brak pluginu → blocked (nie fallback keyboard)

**Kryterium akceptacji:** Scenariusze w `nlp2uri/testql-scenarios/` + smoke w Koru `test_nlp2uri_control_bridge.py`.

**Zrealizowane pliki:** `nlp2uri/testql-scenarios/koru-ide-control-roundtrip.testql.toon.yaml`, `tests/test_koru_ide_systemmap.py`, `tests/test_koru_control_execute.py`, `koru/tests/test_ide_status_systemmap.py`, `koru/tests/test_nlp2uri_ide_control_gate.py`.

---

## Harmonogram (sugerowany)

```text
Tydzień 1:  Faza 0 (docs) + Faza 1 (registry)
Tydzień 2:  Faza 2 (ControlAction + compile)
Tydzień 3:  Faza 3 (driver) + Faza 4 (MCP Koru)
Tydzień 4:  Faza 5 (parser NL)
Tydzień 5:  Faza 6 (SystemMap) + Faza 7 (TestQL)
```

Fazy 5 i 6 mogą iść równolegle po Fazie 2.

---

## Zmiany w Koru (bez refaktoru koruide)

| Plik / obszar | Zmiana |
|---------------|--------|
| `src/koruapi/mcp_server.py` | `koru_ide_drive`, `koru_ide_status` |
| `src/koruapi/desktop_uri.py` | routing IDE intents do control compile |
| `src/koru/autonomous_cycle_gate.py` | opcjonalna ścieżka `KORU_IDE_CONTROL_VIA_NLP2URI` |
| `src/koru/control_commands.py` | JSON Schema export dla nlp2uri validation |
| `docs/*` | utrzymanie cross-linków |

**Bez zmian** w: `handlers_drive.py`, `probe-ladder.ts`, `plugin_router.py` (poza ewentualnym exporterem status → SystemMap).

---

## Zmiany w nlp2uri

| Obszar | Zmiana |
|--------|--------|
| `schemas/registry.yaml` | schematy `ide_*`, `koru_control` |
| `src/nlp2uri/models.py` | `IntentKind` + `ControlAction` |
| `src/nlp2uri/compile.py` | `compile_control_uri` |
| `src/nlp2uri/parse_nl.py` | intencje IDE |
| `src/nlp2uri/adapters/koru.py` | nowy driver |
| `src/nlp2uri/adapters/mcp.py` | control tools |
| `SUMD.md` | sync z docs Koru |
| `pyproject.toml` | optional `[koru]` extra |

---

## Metryki sukcesu

| Metryka | Cel |
|---------|-----|
| NL → IDE chat send (dry-run) | < 100 ms bez socket I/O |
| Replay CLI z planu | identyczny wynik co ręczne `koru autopilot drive` |
| Brak regresji desktop URI | istniejące testy `nlp2uri` green |
| Dokumentacja | jeden punkt wejścia: `ide-control-architecture.md` |
| Autonomous | opcjonalna ścieżka bez duplikacji fallback logic |

---

## Ryzyka

| Ryzyko | Mitygacja |
|--------|-----------|
| Duplikacja logiki drive | Execute tylko przez `KoruIDEClient`; nlp2uri = compile |
| URI z tekstem w query | Walidacja + odrzucenie; `text` tylko w body |
| Cross-repo drift wersji | TestQL + pinned `nlp2uri>=X` w `koru[desktop]` |
| Cursor focus bugs mylone z nlp2uri | Docs: runtime ≠ planning layer |
| Circular import Koru↔nlp2uri | Driver jako optional extra; lazy import |

---

## Definition of Done (cały program)

- [ ] Wszystkie fazy 1–7 zamknięte lub jawnie deferred z ADR
- [ ] `koru ide doctor` nie regresuje
- [ ] `nlp2uri` release notes + bump minor
- [ ] Przykład w `examples/nlp2uri-koru-ide-control/` (opcjonalnie)
- [ ] Aktualizacja `agent-guide.md` — kiedy używać MCP desktop vs ide drive

---

## Powiązane plany

| Plan | Relacja |
|------|---------|
| [REFACTORING_PLAN.md](../refactoring/REFACTORING_PLAN.md) | Hotspoty Koru (daemon, doctor) — ortogonalne |
| [adr-kide-001](../adr/adr-kide-001-koru-vs-koruide-boundary.md) | Granica koru/koruide — respektowana |
| [package-extraction-plan.md](../package-extraction-plan.md) | Ekstrakcja koruide — po stabilizacji API |
| [observation-mesh-plan.md](observation-mesh-plan.md) | Telemetry mesh — Faza 6 może się złączyć |
| `nlp2uri/SUMD.md` | Lustrzana sekcja integracji |
