# Plan Refaktoryzacji koru (na podstawie SUMD.md)

**Wersja:** 1.0
**Data:** 2026-05-25
**Źródło danych:** `SUMD.md` (Call Graph: 404 węzłów, 500 krawędzi, 92 moduły, CC̄=3.8) + statystyki LOC

## 1. Krytyczne hotspoty (priorytet ⚠️ HIGH)

| Moduł / funkcja | LOC | CC | in | out | Problem |
|---|---|---|---|---|---|
| `src/koruapi/dashboard_routes.py::_build_dashboard_handler_impl` | 592 | 1 | 1 | **267** | God-function: 17+ route handlers w nested closure, powtarzający się boilerplate `try/except → _send_json` |
| `src/koru/doctor.py` | 2083 | 6 | – | 11 | Największy moduł – wymaga rozbicia na pod-domeny diagnostyczne |
| `src/koru/autonomous_cycle_chat_activity.py` | 1185 | – | – | – | Zbyt duża odpowiedzialność (chat activity + analiza) |
| `src/koru/scan.py::run_scan` | 1104 | **15** | 4 | 29 | Najwyższe CC w projekcie – wymaga rozbicia na pipeline kroków |
| `src/koru/autopilot/cli_command.py` | 1084 | – | – | – | Mega-CLI do rozbicia per-subcommand |
| `src/koruapi/mcp_server.py::tool_run_ticket` | 1023 | **12** | 1 | 31 | Wysoka złożoność |
| `src/koru/autonomy/operator_pipeline.py` | 1016 | – | – | – | Pipeline operatora do zdekomponowania |
| `src/koruide/daemon/handlers.py` | 998 | – | – | – | Zbiór handlerów do podziału per-typ wiadomości |
| `src/koru/context_render.py::render_markdown_handoff` | 472 | **10** | 6 | 47 | Wysoka złożoność renderingu, dużo zewnętrznych zależności |
| `src/koru/queue/loop.py::run_planfile_queue_loop` | 115 | **14** | – | 9 | Wysokie CC mimo małej LOC – złożona logika sterowania |
| `src/koruide/ide.py::detect_running_ides` | 746 | **13** | 24 | 10 | Złożona detekcja procesów IDE |
| `src/koruapi/cli.py::main` | 137 | **11** | – | 21 | Mega-`main()` |

## 2. Wzorce do refaktoryzacji

### A. Powtarzający się boilerplate HTTP w `dashboard_routes.py`

Każda metoda route handlera zawiera ten sam schemat:

```python
def _get_X(self) -> None:
    try:
        project = self._selected_project()
        result = some_payload(project)
    except ValueError as exc:
        self._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:
        self._send_json({"error": str(exc), "type": type(exc).__name__}, status=500)
        return
    self._send_json(result)
```

**Rozwiązanie:** Helper `_handle_request()` lub dekorator `@route_handler` upraszczający do:

```python
def _get_X(self) -> None:
    self._handle_request(lambda: some_payload(self._selected_project()))
```

**Korzyść:** redukcja LOC o ~30%, eliminacja duplikacji, jeden punkt mapowania błędów.

### B. Nested closure-based handlers w `_build_dashboard_handler_impl`

17+ metod zdefiniowanych wewnątrz funkcji aby zamknąć `config`. Powoduje:
- Nieczytelny call-graph (out=267)
- Trudne testowanie pojedynczych routes
- Brak izolacji per-resource

**Rozwiązanie:** Przejście na klasę `DashboardHandler` z `__init__` przyjmującym `ServeConfig`:

```python
class DashboardHandler(DashboardRequestHandler):
    config: ClassVar[ServeConfig]  # injected by factory

    def _get_dashboard(self) -> None: ...
```

Plus router-as-data:

```python
GET_ROUTES = {
    "/api/dashboard": DashboardHandler._get_dashboard,
    "/api/config": DashboardHandler._get_config,
    ...
}
```

### C. Mega-CLI w `autopilot/cli_command.py` i `cli.py`

**Rozwiązanie:** Subcommand registry (jeden plik per subcommand w `src/koru/autopilot/commands/`):

```
src/koru/autopilot/commands/
  __init__.py     # rejestr
  daemon.py
  drive.py
  status.py
  doctor.py
  ...
```

### D. `run_scan` i `doctor.py` jako pipeline-y

**Rozwiązanie:** Wzorzec `Step` / `Stage`:

```python
class ScanStage(Protocol):
    name: str
    def run(self, ctx: ScanContext) -> StageResult: ...

PIPELINE: list[ScanStage] = [DetectStage(), AnalyzeStage(), ReportStage()]
```

Łatwe dodawanie/wyłączanie etapów + telemetria.

## 3. Plan fazowy

### FAZA 1 — Quick wins (1–2 dni)
- [x] **R1**: `dashboard_routes.py` – ekstrakcja helpera `_safe_respond_json()` (commit `bdd2bf1`, -39 LOC, 0 zmian zachowania)
- [x] **R2**: `dashboard_routes.py` – wyciągnięcie HTML response builderów do `dashboard_html.py` (-49 LOC, +8 testów)
- [x] **R3**: `koruapi/cli.py::main` – rozbicie na subcommand dispatcher (`main` CC: 11 → 3, +2 testy zabezpieczające spójność dispatch table)
- [x] **R-IM1**: `install_manager.py` – ekstrakcja 11 funkcji `_check_*` + `ManagerIssue` do `install_checks.py` (`install_manager.py`: 734 → 466 LOC, **-36.5%**; +23 testy jednostkowe; legacy `_check_*` aliasy zachowane dla backward-compat z testami)

### FAZA 2 — Rozbicia modułów (3–5 dni)
- [ ] **R4**: `dashboard_routes.py` – migracja z closure do ClassVar config injection
- [ ] **R5**: `autopilot/cli_command.py` – podział na `commands/{daemon,drive,status,doctor}.py`
- [ ] **R6**: `koruide/daemon/handlers.py` – podział per typ wiadomości
- [ ] **R7**: `autonomous_cycle_chat_activity.py` – wyciągnięcie analizy do `chat_activity_analyzer.py`

### FAZA 3 — Pipeline-y (5–7 dni)
- [ ] **R8**: `scan.py::run_scan` – pipeline ScanStage
- [ ] **R9**: `doctor.py` – pipeline DiagnosticStage + per-domain modules
- [ ] **R10**: `autonomy/operator_pipeline.py` – formalizacja jako pipeline + dependency injection
- [ ] **R11**: `queue/loop.py::run_planfile_queue_loop` – ekstrakcja stanów do state machine

### FAZA 4 — Złożoność funkcji (3–5 dni)
- [ ] **R12**: `context_render.py::render_markdown_handoff` – wyciągnięcie 47 wywołań do strategii renderowania per-sekcja
- [ ] **R13**: `koruide/ide.py::detect_running_ides` – wyciągnięcie detektorów per-platforma (WMC: Linux/Wayland/X11/JetBrains)
- [ ] **R14**: `mcp_server.py::tool_run_ticket` – Strategy pattern dla typów ticketów

### FAZA 5 — Architektura (continuous)
- [ ] **R15**: Integracja `deployment_events` z istniejącymi flowami (install_manager, autonomous, daemon)
- [ ] **R16**: Migracja pozostałych compat shims (`koru.autopilot.*`) zgodnie z ADR-KIDE-001
- [ ] **R17**: Konsolidacja CQRS event bus (obecnie 2 systemy: `cqrs/event_bus.py` + `events.py` + `deployment_events.py`)

## 4. Metryki sukcesu

Po każdej fazie generować nowy `SUMD.md` i porównywać:

| Metryka | Baseline (2026-05-25) | Target FAZA 1 | Target FAZA 3 |
|---|---|---|---|
| Hub `_build_dashboard_handler_impl` out | 267 | ≤150 | ≤80 |
| Max LOC w module | 2083 (doctor) | 2083 | ≤800 |
| Max CC w funkcji | 15 (run_scan) | 15 | ≤8 |
| Modules CC̄ | 3.8 | ≤3.5 | ≤3.0 |
| Liczba modułów | 92 | 95 | 110+ |

## 5. Zasady refaktoryzacji

1. **Test-first**: brak refaktora bez pokrycia testowego ścieżki happy-path
2. **Małe kroki**: każdy R# = jeden commit, ≤300 LOC zmian
3. **Compat shims**: gdy refaktor zmienia API, zostawić alias re-eksport (jak `koru.autopilot.ide` → `koruide.ide`)
4. **Brak nowej funkcjonalności**: refaktor wyłącznie reorganizuje; nowe funkcje w osobnych ticketach
5. **Telemetria**: nowo wprowadzone pipeline-y emitują `DeploymentEvent` (z `src/koru/deployment_events.py`) dla obserwowalności

## 6. Powiązane dokumenty

- `docs/adr/adr-kide-001-koru-vs-koruide-boundary.md` – granica koru ↔ koruide
- `docs/specs/kide-002-koruide-api-v1.md` – API v1 koruide
- `docs/specs/kide-003-koruide-api-v2.md` – planowane API v2
- `docs/deployment-events.md` – system zdarzeń deploymentu
- `TODO.md` – plan KIDE-* (ekstrakcja koruide)
