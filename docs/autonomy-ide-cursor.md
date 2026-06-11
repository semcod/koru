# Autonomia koru a Cursor IDE — luka i checklista wdrożeniowa

## Podsumowanie

**Częściowa autonomia `koru autonomous`:** koru potrafi orkiestrować pracę wokół ticketów, planfile i bramek jakości, ale pełna „autonomia agenta” w sensie sterowania IDE jak natywny klient Cursor **nie jest** celem ani stanem obecnym — jest to **świadomie ograniczona** autonomia oparta na tym, co da się zrobić stabilnie bez nieudokumentowanego API producenta IDE.

### VQL + vdisplay desktop autonomy progress (2026-06-11)
- **VQL metadata analysis** saved: [.vdisplay/2026-06-11-vql-metadata-analysis-previous-current.json](.vdisplay/2026-06-11-vql-metadata-analysis-previous-current.json) — compares previous (Invalid session, unbound meta, wrong regions, virtual black 1280x720 VQL) vs current (portal-screencast+stream DP-1 region 0/652/2048/1280, nodes 86/133/100, keeper delegation, rich NL "#181818 4 duże regiony", full monitors+nl, data_locations with png/.env/vdisplay_client.py/planfile paths, **click_center {x:1024, y:640}** for mouse nav on DP-1 capture frame, decision_data for Cursor chat/editor/terminal, actionable observe-decide-act loop).
- **Preflight status**: vdisplay agent healthy, screencast active/ready, **keeper running + capture_ready: true** (socket /run/user/1000/vdisplay-screencast.sock) — delegation works, no more AccessDenied.
- **LLM decision** (via .env OPENROUTER + gemini-3.5-flash on live /tmp/vdisplay-dev-dp1.png + VQL): synthesized in .vdisplay/llm-decision-2026-06-11.json (visible: Cursor "vdisplay console" tab + koru terminal + planfile open; 3 actions: load VQL in client, add planfile autonomy task, vision control test; planfile sugg: autonomy-vql-llm-001).
- **Integration**: `load_vql_metadata()` added to src/koru/integrations/vdisplay_client.py (returns click_center, data_locations, decision_data from the analysis or per-capture .vql). Use for hybrid vision + explicit coords in send_chat / verify.
- **Artifacts persisted** to .vdisplay/ (png, .vql.json, context, decision, raw).
- **Next for full loop**: `vdisplay agent screencast probe --source DP-1`; `vdisplay control find --backend vision --vision-anchor "planfile" --source DP-1`; feed VQL to LLM; drive control_set/click or send_chat on visible Cursor regions. This + keeper ready advances "używaj tego komputera do rozwoju programu via vdisplay" (self-edit koru/vdisplay using its own GUI + VQL decisions).
- Related: docs/plans/capture-providers-refactor.md (koru portal) + the vdisplay VQL enables the control half of autonomy.

**Autopilot (`koru autopilot`)** to w praktyce **wstrzykiwanie promptów** do czatu IDE (wklejka + submit), a nie pełne API Cursor ani pełna kontrola nad modelem, narzędziami agenta ani cyklem sesji po stronie Cursor. Działa to jak **most terminal ↔ pole czatu**, nie jak headless agent API.

**MCP** w stacku koru jest **osobnym torem** (konfiguracja serwerów MCP, provisioning, integracja z workflow) — nie należy mylić go z autopilotem: MCP rozwiązuje integrację narzędzi z LLM w IDE, ale **nie zastępuje** protokołu odczytu odpowiedzi LLM ani jednolitego kanału shell↔IDE w sensie sterowania agentem.

### Aktualny stan implementacji

**Zaimplementowane:**
- [x] `koru autonomous up` — pętla orkiestracji autonomicznej (scan → queue → autopilot)
- [x] `koru autopilot daemon` — unix-socket broker z SO_PEERCRED
- [x] `koru autopilot drive` — wstrzykiwanie tekstu do czatu IDE
- [x] `koru autopilot handoff` — jednorazowe wstrzyknięcie bieżącego briefu koru do IDE
- [x] Daemon-side handoff — obsługa zdarzenia `session.ended`, gdy klient IDE je wyemituje
- [x] VS Code/Windsurf plugin — rozszerzenie z protokołem NDJSON
- [x] Keyboard simulation fallback — xdotool/wtype/ydotool
- [x] WUP integration — `--wup-watch` z testql mode
- [x] Idle diagnostics — regix, redup, testql, redsl, sumr
- [x] Idle project discovery — pusta kolejka moze uruchomic `code2llm -f all`
      i wygenerowac nowe tickety `planfile` z analizy calego projektu
- [x] Post-run verify — `queue.post_run_verify` in `koru.yaml` (queue + IDE `done` detection)
- [x] Diagnostic tickets — automatyczne tworzenie ticketów przy błędach
- [x] Topology integration — `.koru/topology.yaml` toggles

**Braki funkcjonalne (vs pełna autonomia):**
- [ ] Odczyt odpowiedzi LLM z IDE (read-side)
- [x] Realne zdarzenie zakończenia sesji z API IDE, nie tylko ścieżka obsługi po stronie daemona (VS Code plugin obsługuje `session.ended`)
- [ ] Sterowanie narzędziami agenta (edycja plików, terminal IDE)
- [ ] Jeden spójny kanał shell ↔ IDE (stdout/stderr agenta vs zdarzenia czatu)
- [ ] Centralna polityka IDE sterowana z koru
- [ ] Twarde powiązanie ticketów z sesją IDE

### Co brakuje do „pełnej” integracji z IDE (Cursor)

| Obszar | Co brakuje (krótko) |
|--------|----------------------|
| **Odczyt odpowiedzi LLM** | Brak niezawodnego, wspieranego oficjalnie sposobu na odczyt treści odpowiedzi modelu z czatu do procesu zewnętrznego (zamknięta pętla bez OCR / hacków). |
| **Sterowanie narzędziami agenta** | Autopilot nie wywołuje narzędzi agenta (edycja plików, terminal IDE) programistycznie — tylko dostarcza tekst do czatu. |
| **Jeden kanał shell ↔ IDE** | Terminal i IDE nie mają jednego spójnego duplexowego kanału zdarzeń (stdout/stderr agenta vs. zdarzenia czatu); są to osobne światy zszywane heurystykami. |
| **Polityka IDE** | Brak centralnej polityki po stronie IDE (np. „czy wolno commitować”, „jakie MCP”, limity tokenów) sterowanej z koru — użytkownik i konfiguracja IDE nadal są źródłem prawdy. |
| **Powiązanie ticketów z sesją** | Ticket w planfile nie jest natywnie „sesją” Cursor; brak twardego ID sesji IDE ↔ PLF-XXX w protokole producenta. |

---

## Checklista uruchomienia obecnej autonomii

### Krok 1: Wymagania systemowe

- [ ] **Python 3.12+** z `pip` i `venv`
- [ ] **System operacyjny Linux** (X11 lub Wayland)
- [ ] **IDE**: VS Code, VSCodium, Windsurf, Cursor, JetBrains albo Zed
- [ ] **Backend wstrzykiwania tekstu**: preferowany plugin VS Code/VSCodium/Windsurf/Cursor; fallback X11 `xdotool`, Wayland `wtype` albo `ydotool`
- [ ] **Clipboard tools**: `wl-clipboard` lub `xclip`, gdy używasz backendu klawiaturowego

### Krok 2: Instalacja koru

- [ ] **Klonowanie repozytorium**: `git clone https://github.com/semcod/koru.git`
- [ ] **Wirtualne środowisko**: `python3 -m venv .venv && source .venv/bin/activate`
- [ ] **Instalacja w trybie editable**: `pip install -e .`
- [ ] **Weryfikacja instalacji**: `koru --help`
- [ ] **Inicjalizacja projektu**: `koru --init` (tworzy `.planfile/`)

### Krok 3: Konfiguracja autopilota

- [ ] **Diagnostyka hosta**: `koru autopilot doctor` i opcjonalnie `koru autopilot setup-host --install`
- [ ] **Instalacja/naprawa pluginu IDE**: `KORU_AUTOPILOT_INSTANCE=vscode koru autopilot manage --ide vscode --fix`
- [ ] **Uruchomienie daemona w terminalu**: `koru autopilot daemon --project "$(pwd)"`
- [ ] **Weryfikacja połączenia**: `KORU_AUTOPILOT_INSTANCE=vscode koru autopilot status` oraz `KORU_AUTOPILOT_INSTANCE=vscode koru autopilot manage --ide vscode`
- [ ] **Test wstrzykiwania**: `KORU_AUTOPILOT_INSTANCE=vscode koru autopilot drive --ide vscode --require-plugin 'test prompt'`
- [ ] **Opcjonalnie: systemd user unit**: `koru autopilot install-unit --force`, potem `systemctl --user daemon-reload && systemctl --user enable --now koru-autopilot`

### Krok 4: Konfiguracja autonomous mode

- [ ] **Podstawowa pętla**: `koru autonomous up --project . --ticket-sources all --max-cycles 0`
- [ ] **Konfiguracja agent lane**: `--agent-lane=cursor` (lub `windsurf`, `local`)
- [ ] **Włączenie diagnostyki idle**: `--idle-diagnostics=full --diagnostic-tickets`
- [ ] **Konfiguracja WUP** (jeśli dotyczy): `--wup-watch --wup-mode testql --wup-diagnostic-tickets` oraz `wup.yaml` w katalogu projektu
- [ ] **Topologia** (opcjonalnie): `.koru/topology.yaml` z toggles dla komponentów

### Krok 5: Walidacja

- [ ] **Test diagnostyki**: `koru autonomous up --idle-diagnostics=quick --max-cycles=1`
- [ ] **Test WUP** (jeśli skonfigurowany): Sprawdź `.wup/service-health.json`
- [ ] **Test autopilot drive**: `KORU_AUTOPILOT_INSTANCE=vscode KORU_STRICT_PLUGIN_VERSION=1 koru autopilot drive --ide vscode --require-plugin 'continue with next ticket'`
- [ ] **Test handoff**: `KORU_AUTOPILOT_INSTANCE=vscode koru autopilot handoff --ide vscode --require-plugin`
- [ ] **Sprawdź logi**: `koru autopilot tail`

---

## Lista zadań wdrożeniowych (dla deweloperów)

### Protokół IDE

- [x] **Zdarzenia `session.ended`** — emitowanie i konsumpcja na kanale socket/NDJSON między daemonem a rozszerzeniem IDE (spójny kontrakt, nie tylko heurystyka czasu).
- [ ] **Read-side odpowiedzi LLM** — prototyp odczytu treści ostatniej odpowiedzi z dokumentu czatu (`openTextDocument(chatUri)` lub równoważnik) z testem integracyjnym na jednym IDE.
- [x] **Wersjonowanie protokołu** — pole `protocol_version` w każdej ramce NDJSON i test odrzucenia niezgodnych klientów.
- [x] **Heartbeat / reconnect** — metryka „czas od ostatniego ping” w `koru autopilot status` + automatyczne ponowne podłączenie rozszerzenia po restarcie IDE.

### Integracja planfile

- [x] **Append wyniku shell do opisu ticketu** — po sukcesie `executor.kind=shell` w `run_next_planfile_task` kolejno: `planfile ticket update <id> --note`, przy braku opcji w CLI (`No such option`) próba `-n`, a gdy obie brakują (np. starsze 0.1.x) zapis `KORU-SHELL-RUN` + stdout/stderr do `.planfile/.koru/runs/<id>-<run_id>.shell-evidence.txt` (tail-truncate, `run_id` w JSON). Przy błędzie realnego `update` (nie „unknown option”) log `warning`, potem i tak `ticket done`. Helpery: `format_shell_run_note`, `append_shell_evidence_note`.
- [ ] **`ticket claim` ↔ sesja autopilota** — zapis `actor` + `lease` + hash ostatniego promptu w metadanych ticketu (audyt: kto i co wstrzyknął).
- [ ] **Handoff kolejki** — przy `session.ended` automatyczne `planfile ticket show` następnego PLF z etykietą `koru` i wstrzyknięcie skrótu ≤ N znaków do czatu (test E2E na fixture).

### MCP

- [ ] **Manifest MCP w repo** — jeden plik źródłowy prawdy (`mcp.json` / template) generowany przez `koru` z walidacją schematu JSON.
- [ ] **Test smoke: MCP start/stop** — test CI uruchamiający minimalny serwer MCP z `stdio` i asercją na handshake (bez sieci zewnętrznej).
- [ ] **Mapowanie narzędzi MCP → planfile** — dokument + przykład: które narzędzie MCP aktualizuje które pole ticketu (kontrakt dla agentów).

### Bezpieczeństwo i UX

- [ ] **Allowlista komend shell** z planfile — konfiguracja regex + test odrzucenia komend spoza listy dla `run_next_planfile_task`.
- [x] **Rate-limit `drive`** — max N wiadomości/min na socket per UID z komunikatem błędu i logiem audytowym.
- [x] **UX: podgląd runtime autopilota** — `koru autopilot status` + `koru autopilot manage --ide vscode` pokazują socket, podłączone pluginy, wersje `connected/installed/expected` i backendi wstrzykiwania.
- [x] **Audit log** — NDJSON log at `$XDG_STATE_HOME/koru/autopilot.log` z rotacją 10 MiB, zdarzenia: `daemon_started`, `daemon_stopped`, `plugin_connected`, `drive`, `handoff`, `shutdown`.

### Testy

- [x] **Test: pełna ścieżka daemon → mock IDE** — fixture socket + nagranie ramek NDJSON (regresja na limit 1 MiB i typy).
- [x] **Test: `SO_PEERCRED` odrzuca obcy UID** — asercja na odmowę połączenia przy symulowanym innym UID (gdzie środowisko CI na to pozwala; w przeciwnym razie skip z jasnym powodem).
- [ ] **Test kontraktu planfile** — ticket YAML z sekcją „wynik ostatniego runu” po appendzie — diff złoty vs. wygenerowany.

---

## Zobacz też

- [`autopilot-quickstart.md`](./autopilot-quickstart.md) — jak włączyć autopilota z terminala.
- [`autopilot-roadmap.md`](./autopilot-roadmap.md) — fazy P2+ (m.in. `session.ended`, read-side).
- [`planfile-execution-gateway.md`](./planfile-execution-gateway.md) — plan na bramkę wykonania dla wielu aktorów.

### VQL layers progress (continuation after STARTER-011)
- Fresh captures (with imgl + VDISPLAY_VISION_BACKEND=auto) now produce 31 UI elements with explicit centers/bboxes (window 1024,493; buttons e.g. 1219,342 top, 1283,969 bottom, etc.).
- load_vql_metadata() in koru vdisplay_client now parses fresh .vql.json "elements" into ui_elements with click_center, bounds, role.
- resolve_click_for_frame() provides actionable mouse coords from VQL (or analysis).
- In autonomous_cycle_gate.try_vdisplay_control_fallback: now loads VQL and attaches click_center / vql_context to drive reply for better decisions.
- Previous misleading VQL (virtual Xvfb coords) vs current: correct portal capture + real UI layers from detection.
- Next: wire resolve as fallback in _find_first_selector when vision anchor misses; use VQL centers in koru observation for JetBrains/Cursor state (open files, chat input position).
- Gaps documented in .vdisplay/2026-06-11-vql-metadata-analysis-previous-current.json

### Sequential continuation (kontynuuj after STARTER-011 + imgl)
- vdisplay_semantic_control now tried immediately after failed plugin drive (before gillm/os_injector) in autonomous_cycle_drive_retry.py for jetbrains lane when KORU_VDISPLAY_CONTROL_FALLBACK=1.
- _find_first_selector now has vql_fallback (default True): if vision misses anchor, returns VQL center from fresh capture (31 elems with real bboxes/centers from imgl detection) or analysis.
- VQL load/resolve integrated into try_vdisplay fallback in gate, so drive replies include click_center + vql_context for autonomy decisions.
- Tested: load fresh gives 31 ui_elements with centers; fallback provides coords for act.
- Result: in koru autonomous for vdisplay project (as in user log), with proper env + local install, will use semantic vdisplay control + VQL mouse coords (e.g. 1024,493 window or button centers) instead of pure os_injector keyboard. Better observe (rich VQL layers) -> decide (with data_locations, decision_data) -> act (precise click/focus in JetBrains UI).
- Next user step: in vdisplay dir, `pip install -e .` (local vdisplay), set exports, re-run `coru` (jetbrains). See vdisplay backend + VQL in logs for STARTER-011 drives.

### P0/P1 closure (kontynuuj)
- get_vql_target() added: selects from VQL ui_elements/layers by role/name_contains/label, returns click_center/bounds/id for use in decide/act (addresses missing layers -> target gap).
- send_chat for jetbrains now falls back to VQL target for chat input (synthetic selector with click_point from VQL, not stub 0x0).
- vdisplay now early in fallback chain before os_injector.
- load normalizes to layers + ui_elements for consumers.
- With imgl + VDISPLAY_VISION_BACKEND=auto + KORU_VDISPLAY_CONTROL_FALLBACK=1, observe produces rich detection layers, decide uses VQL targets, act uses real centers.
- Audit: record_koru_drive_step already uses VDISPLAY_SESSION when set; set in env for auto runs.
- Test: get_vql_target returns centers; integration ready for jetbrains autonomy loop.

### P1 spójność pętli (kontynuuj)
- VDISPLAY_SESSION=1 now auto-set in vdisplay fallback gate, and record_koru_drive_step called to persist to .vdisplay/ session (addresses "vdisplay auto nie ustawia VDISPLAY_SESSION" and audit bypass).
- VQL context (layers, click_centers, data_locations) now in drive payload for verify/audit.
- With this + previous, when re-running koru in vdisplay/jetbrains with the env, full observe (rich VQL from imgl) -> decide (VQL target) -> act (coords) -> verify (with context) -> audit (session events) loop.
- Next: user to set envs and re-run to see VDISPLAY backend + session recording in logs for STARTER-011.
