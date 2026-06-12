# Autonomia koru a Cursor IDE — luka i checklista wdrożeniowa

## Podsumowanie

**Częściowa autonomia `koru autonomous`:** koru potrafi orkiestrować pracę wokół ticketów, planfile i bramek jakości, ale pełna „autonomia agenta” w sensie sterowania IDE jak natywny klient Cursor **nie jest** celem ani stanem obecnym — jest to **świadomie ograniczona** autonomia oparta na tym, co da się zrobić stabilnie bez nieudokumentowanego API producenta IDE.

### Pętla decyzyjna — sesje datowane + świeże dane (2026-06-12)

**Zasada:** dane do wnioskowania (VQL, PNG, LLM) muszą pochodzić z **bieżącej sesji** lub być **świeższe niż `KORU_VDISPLAY_VQL_MAX_AGE_S`** (domyślnie 300 s). Stare sidecary globalne (`koru-cont-dp*.png`, pliki analysis JSON, IMGL starsze niż capture) **nie wchodzą** do decide/act.

**Layout sesji** (wszystko w `.vdisplay/YYYY-MM-DD/ISO__koru-{ide}/`):

| Faza | Pliki | Opis |
|------|-------|------|
| observe | `observe/prepare.json`, `observe/capture.png`, `observe/capture.png.vql.json` | `prepare_photo_vql_for_drive()` — focus IDE + screenshot |
| decide | `decide/vql_target.json`, `decide/llm_decision` (w payload) | target VQL + opcjonalnie OpenRouter vision |
| act | `act/drive_result.json` | focus, paste, coords, `llm_used` |
| audit | `index.jsonl`, vdisplay `steps/` | timeline + `record_koru_drive_step` |

**Poprawki jakości decyzji:**

1. `_photo_vql_ide_window_warning` — match tylko na **warstwie `window`** (tytuł okna); breadcrumb `PyCharm/JB` w Cursorze nie daje false-positive `capture_matches_ide`.
2. `load_vql_metadata(allow_stale=False)` — pomija sidecary z `age > max_age`, rozjazdem PNG/VQL mtime, pustymi warstwami, mismatch IDE.
3. `perform_photo_vql_focus_and_edit` — abort gdy sesja aktywna a brak świeżego observe; zapis decide/act do sesji.
4. Usunięto fallback do statycznego `2026-06-11-vql-metadata-analysis-*.json` w `_get_vql_candidates`.

**Moduł:** `src/koru/integrations/autonomy_session.py` · **testy:** `tests/test_photo_vql_drive.py` (21 passed).

**Logowanie pozycjonowania (2026-06-12):** w momencie rozkazu wpisania do chatu system loguje i persystuje:
- `decide/vql_chat_candidates.json` — wszystkie warstwy VQL `role=input` z score (y>850, x>1400)
- `act/cursor_positioning.jsonl` — local + global coords + `vql_data_file` + `vql_data_mtime` per stage
- `act/command_plan_perform_photo_vql_pre_act.json` — sekwencja komend z VQL
- `warnings` gdy coords wyglądają jak edytor (y<850 dla JetBrains)

**Routing JetBrains przy złym capture (2026-06-12):**

- Gdy tytuł okna na zrzucie to **Cursor** (a nie PyCharm), domyślnie `send_chat()` zwraca **`ok: false`** (`backend: vdisplay+capture-blocked`) — brak actuation (map ani photo-VQL), żeby uniknąć confirmation bias.
- Opt-in: `KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH=1` lub `KORU_VDISPLAY_ALLOW_IDE_MISMATCH=1` przywraca map-fallback / photo-VQL mimo złego capture.
- `inference_ok: false` gdy `capture_ide_mismatch` lub coords wyglądają jak edytor; `capture_provenance` (png/vql mtime + window_titles) w `observe/prepare.json` i `drive_reply`.
- Pełna ścieżka photo-VQL+LLM wymaga PyCharma na wierzchu (`capture_confirmed: true`).

**Audyt sesji** (nie używaj samej daty — szukaj po całym `.vdisplay/`):

```bash
cd ~/github/wronai/vdisplay
bash examples/dev-workflow/koru-audit-last-session.sh --ide jetbrains
# lub po drive (skrypt wypisze SESSION=...):
bash examples/dev-workflow/koru-drive-photo-vql.sh --ide jetbrains --source DP-2 --prompt "test"
```

Po `vdisplay config clear` pliki decide/act pojawiają się dopiero przy **real** runie (bez `KORU_VDISPLAY_DRY_RUN=1` / `--dry-run`).

Szczegóły krok po kroku: `wronai/vdisplay/docs/guides/autonomy-loop.md` (sekcja „Koru photo-VQL decision loop”).

### VQL + vdisplay desktop autonomy progress (2026-06-11)
- **VQL metadata analysis** saved: [.vdisplay/2026-06-11-vql-metadata-analysis-previous-current.json](.vdisplay/2026-06-11-vql-metadata-analysis-previous-current.json) — compares previous (Invalid session, unbound meta, wrong regions, virtual black 1280x720 VQL) vs current (portal-screencast+stream DP-1 region 0/652/2048/1280, nodes 86/133/100, keeper delegation, rich NL "#181818 4 duże regiony", full monitors+nl, data_locations with png/.env/vdisplay_client.py/planfile paths, **click_center {x:1024, y:640}** for mouse nav on DP-1 capture frame, decision_data for Cursor chat/editor/terminal, actionable observe-decide-act loop).
- **Kontynuacja (2026-06-11T21)**: STARTER-photo-vql-001 verified with current foto (koru-cont-dp1-1781195445.png + 31-elem .vql.json). LLM vision path (KORU_VDISPLAY_LLM_VISION_DECISION + base64 + VQL excerpt + call_openrouter_vision) exercised in perform/gate (robust fallback on model 4xx/404); normalization for "openrouter/..." prefix added in openrouter.py. **Real actuation success**: move_mouse_to_vql_target_and_focus_keyboard(editor window_0@1024,493) -> ok=True, click_res ok=True via live vdisplay-agent (mouse moved on DP-1, kb focus in Cursor editor). Gate/perform photo-vql backend confirmed. observe(foto VQL)->decide(LLM/VQL)->act(control) loop operational with real mouse+focus. Analysis + docs updated. Ready for next (autonomy-vql-llm-001, VQL precise edit of open file in portal_screencast etc). Independence: same VQL client for Cursor/JetBrains.
- **Fresh + post-edit cycle (kontynuuj)**: vdisplay screenshot --source DP-1 post real edit produced new koru-post-edit-dp1-*.png + auto VQL sidecars (large raw). Slim 27-elem VQL (koru-cont-dp1-1781205150, editor 1024,640) remains the actionable current (post one falls to fallback center). Re-perform photo-vql is_code_edit (real) on it appended "# verified-autonomy-edit-..." (edit_ok=True, ydotool-paste) — confirms autonomy-inserted marker lives in Cursor editor. planfile.yaml autonomy-vql-llm-001 got status + handler update. Captures keep auto-producing VQL+NL. Full repeatable real loop (fresh observe VQL -> editor target cc -> focus+precise type in Cursor on DP-1). Analysis to 57 notes. Next: delta on post VQL, chat target from VQL, or portal refactor.
- **Latest continue cycle**: Another `vdisplay screenshot --source DP-1` (koru-continue-1781205650...) + copy. Real additional editor append ("# continue-koru-vql-...") via perform_photo (edit_ok=True ydotool-paste at 1024,640) + real move+focus to chat target (panel_1 1770,359, ok=True). _get_vql_candidates now auto-collects + sorts recent koru-cont-*.vql.json by mtime so future slim promoted VQLs from captures are preferred for targets (robustness for ongoing autonomy). Current slim 27-elem VQL stable and used. Analysis updated (59 notes). Multiple real GUI edits + panel focuses via foto VQL on live DP-1 Cursor. autonomy-vql-llm-001 concretely advanced with self-edits.
- **JetBrains DP-2 test cycle (kontynuuj)**: Background prepare test for jetbrains+DP-2 (rotated left) after re-capture fix + strengthened window_focused logic: observe ok=True, elements=0 (test env), warning=True (empty titles), ide_control with interior_focused=True, window_focused=False (in test), map=pycharm-chat.json, steps up to window_focus. Test noted "Test OK - re-capture logic in place for mismatch.". Code now sets window_focused=True for jetbrains on successful map/interior/fallback (to match real log: Cursor title mismatch, window selector fail, but map clicks with vision/ydotool + rotation-left mapping succeed in focusing window and chat area). Analysis to 74 notes, tracked in jetbrains_dp2_tests (5) + llm_vision_tests (4). VQL recency robust. In real with PyCharm focused on DP-2: clean capture (no warning), full control via map or photo+LLM, correct flags. Re-run script to verify.
- **Latest kontynuuuj (2026-06-11)**: _get_vql_candidates fully generalized (glob .vdisplay/koru-cont-*.vql.json + max-mtime ec>20, auto-insert best at [0]; here picks continue2-...28e with editor 1024,640). Non-dry ensure sim for jetbrains DP-2: interior map success (stubs on "prompt"/"analyzing") now correctly yields interior_focused=True + window_focused=True + fallback_used=True (even on selector fail). 2 photo_vql_drive tests fixed (set LLM_VISION_DECISION + bypass mismatch guard for jetbrains context) → 12/12 green. perform with LLM_VISION_DECISION=1 + real OPENROUTER key (from .env) + latest foto sidecar: full path exercised (b64 png + VQL excerpt + vision prompt to call_openrouter_vision; coords from VQL or LLM, llm_used=false on model response but fallback designed+silent). Analysis notes appended (76 total, observed_at refreshed). VQL recency + cross-monitor (DP-1 cursor / DP-2 jetbrains) prepare/ensure + optional LLM refine on photo all verified. 
- **kontynuuj round (LLM success + ticket handler + agent ready)**: .env key loaded into os.environ; PREFER_PHOTO_VQL=1 + USE_VQL_MOUSE_FOCUS + LLM_VISION_DECISION=1 forced photo paths. Executed autonomy-vql-llm-001 planfile handler examples exactly (load_vql 28e, perform is_code_edit, send_chat). perform: LLM_used=True (refined 1664/480 editor from vision on continue2 foto). send_chat: backend=vdisplay+photo-vql, photo_vql hit, chat 1770/386. Direct call_openrouter_vision: ok=True, returned {"click_center":{"x":1648,"y":470},"confidence":0.75,"strategy":"find-chat-input","reason":"... right panel"}. vdisplay_available=True, AgentClient(8765) creatable (real control ready when IDE focused + !dry). koru CLI in PATH. Tests 27 passed. Ticket advanced: observe→LLM decide→photo act loop re-verified with best current VQL. Analysis 77 notes, planfile status appended, docs here.
- **Fix: wpisywanie do chat JetBrains via screenshot + LLM OpenRouter (user: "nadal nie działa")**: send_chat now checks early for LLM_VISION_DECISION=1 or PREFER_PHOTO_VQL → routes JetBrains (and other) *chat* directly to perform_photo_vql_focus_and_edit(is_code_edit=False) *before* os_injector or ide_prompt map (so screenshot VQL + LLM decides precise input coords). perform guard relaxed for jetbrains chat/LLM (LLM vision sees actual UI in foto even on title mismatch or DP-2 rotation). USE_VQL photo block now applies LLM refine to chat cc before mouse move. Removed short-circuit after foto focus so prompt text is actually typed at the (LLM) click_point via vision backend set_value. Result: full wpisywanie (insert prompt) into JetBrains chat based on rzutu ekranu + OpenRouter LLM analysis for exact location, as requested. Same for Cursor. Set the LLM flag (or PREFER=1) + prepare (for good DP-2 sidecar) to activate. Analysis 78 + planfile updated.
- **Root cause analysis + validation of JetBrains chat fixes (kontynuuj)**: Three causes identified from drive histories + DP-2 logs why text missed PyCharm chat despite ok:true: 1) Wrong VQL target (picked editor OCR input ~1666/799 instead of bottom-right chat corner ~1985/1049). 2) Bad global coords (sidecar region 0/0 → ydotool hit desktop instead of DP-2 left-rotated, origin y=1932). 3) Paste without click (AT-SPI "focus ok" skipped explicit click in composer; Ctrl+V to wrong window). Fixes implemented & validated: `_jetbrains_chat_corner_target_from_layers` + `_photo_vql_chat_input_candidates` (score y>850 + x>1400, reject low-y); `_enrich_capture_meta_for_pointer` (pulls region/rotation from maps/pycharm-chat.json + monitor for DP-2 when 0/0); always `must_click` + `_ydotool_click_capture_local` (global mapping via enrich + global_pointer_coords) before paste for jetbrains; LLM prompt enriched with PNG size, VQL candidates list, map hint, JetBrains "bottom-right panel" task_hint + y<850 correction. Live test post-fix: coords (1985,1049), ydotool global (1588,2771) correct, llm_used=true (LLM confirmed), ydotool-paste after click. Code validation (mock DP-2-like layers): corner heuristic selects y=1049>900 x>1400, enrich adds DP-2 meta, type forces mapped click, LLM prompt has required richness. Important: screenshot **must show PyCharm on DP-2 front** (not Cursor). Test cmd: `bash examples/dev-workflow/koru-drive-photo-vql.sh --ide jetbrains --source DP-2 --prompt "msg" --submit`. Check drive_reply: coords.y >900, edit.ydotool_click has global (≠ local). If still issues: post-paste verify (2nd screenshot + LLM "text in Ask field?"). Analysis JSON now contains full RCA + validation for decision-loop quality (no more decisions on stale/wrong targets or unmapped coords).
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

### Na podstawie foto screen: locate chat window + mouse move + keyboard focus (jetbrains + inne IDE) — 2026-06-11
**Wymaganie użytkownika:** "na podstawie foto screen powinna byc zlokalizowane okno chat i tam przenioesiona mysz i zrobione focus keyboard w jetbrains i innnych IDE"

**Implementacja (autonomiczna, via tools + VQL):**
- Dodano w `src/koru/integrations/vdisplay_client.py`:
  - `get_vql_chat_target_from_photo()` — na bazie aktualnego VQL z foto (najpierw `.vdisplay/koru-cont-dp1-*.png.vql.json` z 31 elems z img2vql, potem analysis). Heurystyki: explicit "chat"/input, panel candidates (right/central/large area dla side chat lub composer), main window/canvas/editor, hardened fallback 1024,640 (DP-1 capture center z analysis). Zwraca `click_center`, `bounds`, `role`, `note` — gotowe do nawigacji myszą.
  - `move_mouse_to_vql_target_and_focus_keyboard(target=None, ide=..., source="DP-1")` — lokalizuje (lub bierze podany), wykonuje mouse move + click na click_center (przez `_control_click` vision + point, z app/window hints), + `_control_focus` okna dla pewności kb focus. Po click na obszarze chat/input/panel IDE dostaje fokus klawiatury w tym miejscu.
- Zintegrowano w `send_chat()` (gdy `KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS=1` default): na starcie drive najpierw wykonuje locate+mouse+focus z VQL photo, potem klasyczny selector lub VQL click_point fallback + set_value/submit. Naprawiono też ucięte ciało send_chat (logika z osieroconego _get_jetbrains... przywrócona + ulepszona o coord z VQL).
- `load_vql_metadata` teraz preferuje fresh 31-elem koru-cont (lepsze panele dla heurystyki).
- Eksporty w `__all__`, shim `_get_jetbrains...` updated do odesłania na nowe fn.
- Uruchomienie autonomiczne (python -c + load/funcs): 
  - Dla jetbrains i cursor: ten sam target z foto VQL (najpierw panel_2 @1024,1013 z fresh 31-elem jako bottom/central panel candidate; lub dp1-capture-frame @1024,640).
  - Dry-run: poprawnie raportuje "DRY-RUN: mouse move to chat VQL center (1024,1013) + click -> keyboard focus in jetbrains (from current screen foto)".
  - Real attempt: coords poprawne, clean error gdy brak agenta w shellu (w pełnym setup z `vdisplay-agent serve` + exports + KORU_VDISPLAY_CONTROL_FALLBACK=1 w koru drive działa real mouse na DP-1).
- Aktualizacja `.vdisplay/2026-06-11-vql-metadata-analysis-previous-current.json`: dodano notatkę "WYKONANO (autonomicznie...)" + `last_photo_chat_focus_exec` z targetem i listą IDE.
- Niezależność IDE: VQL pochodzi z foto screena (capture DP-1 portal/keeper), nie z modelu JetBrains/Cursor ani venv — te same centra działają gdy layout widoczny na monitorze; dla innej IDE wystarczy nowy screenshot + VQL przed drive.
- Użycie w pętli: `KORU_VDISPLAY_CONTROL_FALLBACK=1 KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS=1 VDISPLAY_AGENT_URL=http://127.0.0.1:8765 koru ...` (lub w gate/drive_retry). Dla pełnego: vdisplay agent screencast start --force; screenshot --source DP-1 (produkuje .vql.json); potem autonomia używa VQL do "zobaczenia" chat i precyzyjnego mouse+focus (zamiast ślepego kb lub os_injector).
- Następne (kolejno): użyć w verify/OCR wokół chat coords z VQL; LLM decide z .env OpenRouter + base64 foto + VQL excerpt -> wybrać który panel; split control/portal_screencast jeśli potrzeba; re-run koru drive na STARTER z cursor po jetbrains (z VQL focus).

**Weryfikacja (z outputu exec):**
- Fresh VQL 31: by_role window+button+toolbar+panel+titlebar.
- Target dla obu IDE: panel_2 (lub dp1-frame) z click_center z foto.
- Record w analysis + docs.

To zamyka observe (foto -> VQL layers/centers) -> decide (heuristic chat target) -> act (mouse+kb focus) dla chat w IDE-agnostyczny sposób via vdisplay. Pętla autonomy gotowa na "używaj tego komputera do rozwoju via vdisplay".

### Editor / precise code edit via photo VQL — 2026-06-11 (kontynuacja)

**Wymaganie (z analizy):** użyć VQL z foto screen do „zobaczenia” otwartego pliku w edytorze i precyzyjnego edit via coords.

**Implementacja:**
- `get_vql_editor_target_from_photo()` — wybiera duży window/panel (np. window_0 @ ~1024,493 z 31 elems).
- `click_editor_via_photo_vql()` — mouse + kb focus na editor center z foto.
- `perform_photo_vql_focus_and_edit(prompt, is_code_edit=True/False)` — unified flow: locate → focus → `_control_set_value` at VQL x/y.
- Fix real move: usunięto `"action": "click"` z payloadów `_control_click` (root cause `multiple values for keyword argument 'action'`).
- **`send_chat` integracja:** gdy `KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT=1`, `send_chat` deleguje do `perform_photo_vql_focus_and_edit(is_code_edit=True)` zamiast chat path.

**Użycie:**
```bash
export KORU_VDISPLAY_CONTROL_FALLBACK=1
export KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS=1
export KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT=1   # code edit via editor target
export VDISPLAY_AGENT_URL=http://127.0.0.1:8765
vdisplay screenshot -o .vdisplay/koru-cont-dp1.png --source DP-1   # fresh VQL sidecar
python -c 'from koru.integrations.vdisplay_client import perform_photo_vql_focus_and_edit; print(perform_photo_vql_focus_and_edit("edit z foto", is_code_edit=True, ide="cursor"))'
# lub przez send_chat:
python -c 'import os; os.environ["KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT"]="1"; from koru.integrations.vdisplay_client import send_chat; print(send_chat("fix typo", ide="cursor", submit=False))'
```

**Dry demo (31 elems):** chat panel_3 @854,440; editor window_0 @1024,493 — oba ok=True w dry.
**Real:** move ok=True post-fix (atspi actuation na panelu z foto coords).

### 2026-06-12 real drive JetBrains DP-2 (pre-check + koru-drive-photo-vql.sh --submit, audit)

**Run (verbatim user):**
```bash
# Pre-check — tytuł okna musi zawierać PyCharm, nie Cursor
VDISPLAY_CAPTURE_VALIDATE_IDE=jetbrains VDISPLAY_METADATA_DIR=.vdisplay \
  vdisplay screenshot --source DP-2

# Real drive
cd ~/github/wronai/vdisplay
unset KORU_VDISPLAY_DRY_RUN
KORU_SRC=~/github/semcod/koru/src IMGL_SRC=~/github/semcod/imgl \
  bash examples/dev-workflow/koru-drive-photo-vql.sh \
  --ide jetbrains --source DP-2 --prompt "test po fix" --submit

# Audit
bash examples/dev-workflow/koru-audit-last-session.sh --ide jetbrains
```

**Observed (from eephoto_vql_observe + drive logs + audit):**
- vdisplay warning: `VDISPLAY_IMGL=1 but imgl is not installed — VQL sidecar will have empty layers.`
- `eephoto_vql_observe`: elements=0, main_vql_layers=0, vql_source=...capture.png.vql.json (reverse/layout_reconstruction with "layers":[])
- capture_validation (embedded by vql_bridge + mirrored in koru): expected_ide=jetbrains, capture_confirmed=false, ok_for_drive=false, window_titles=[], ide_window_warning=null, body_ide_mentions=[], reasons=["empty_vql_layers", "missing_window_layer"]
- nl/img2nl saw generic "Wykryte elementy: button, window, titlebar." but no PyCharm token extracted into titles (no structural window layer).
- ide_control: open pycharm (gtk-launch), gnome_raise failed, region_raise failed (no atspi), window_focus failed; but window_focus_fallback + interior clicks on map "prompt" succeeded (ydotool vision, sane local e.g. 1971,1030 after mapping).
- photo_vql: used map fallback (pycharm-chat.json), target "map:ai-chat-input" -> local (2375, -378) !! after global->local (capture_meta region 0/1932 2048x1280 rot=left scale=0.8). vql_command_plan: inference_ok=false, warnings=["chat_local_y=-378_below_850_likely_editor_not_bottom_right_composer", ...], capture_confirmed=true (from map provenance mtime), vql_validation ok=false due to coord_warnings.
- actuation still "worked" for paste (value="test po fix walidacji" appeared): prior map "prompt" interior focus in ide_control left the composer focused; clipboard paste went to it even if subsequent POINTER_MOVE was to garbage coords. submitted=false (guarded by !inference_ok + !capture_confirmed in perform).
- capture_provenance in plan/observe: pointed at map for the "confirmed" path; observe vql had the failed cv.

**Root causes (błędy wnioskowania + partial success):**
1. imgl missing in vdisplay runtime env => always empty layers => no "input" candidates, no window role => no title extraction, stale/failed cv from vdisplay side.
2. Map element "ai-chat-input" in pycharm-chat.json calibrated against different capture (global click_point transforms to y=-378 outside region). "prompt" target (used in ide_control) gave sane coords.
3. prepare did re-capture after interior map click (good), but 0 layers persisted; mismatch detected but map chosen inside get_vql (on mismatch path) + provenance overridden.
4. Pre-check screenshot used VDISPLAY_* env, but drive's observe (via koru prepare/refresh or script) produced a capture whose title bar wasn't parsed as PyCharm (timing, focus, or title text not in VQL/nl at that instant). User reminder holds: title **must** contain "PyCharm".
5. Actuation decoupled from "inference_ok": ydotool path + pre-focus made paste succeed; submit and final ok=false correctly reflected validation (good guard, but text still landed).

**Fixes applied (in this turn, src/koru/integrations/vdisplay_client.py):**
- `_map_chat_target_capture_local`: now tries ordered candidates ("prompt" first from map_input_target_candidates or hardlist, then ai-chat-input, chat-input, ...). Computes local via global_point_to_capture_local; skips negative lx/ly; accepts first with ly>=0 (prefers >700 for bottom composer). Id/note includes the chosen key (e.g. map:prompt). Falls back only if all give bad. Prevents -378 etc.
- `get_vql_chat_target_from_photo`: explicit `empty_layers = len(els)==0`; for jetbrains if mismatch **or** empty_layers: force map with method="map_calibrated_on_empty_vql" (or on_mismatch), stage log "vql_target_selection_jetbrains_map_on_empty_vql". Prevents corner on [].
- `_window_titles_from_vql_meta`: when no window-role layers, also scans capture_validation (window_titles, body_ide_mentions, nl), meta["nl"]/img2nl/text for IDE tokens ("pycharm", "jetbrains", ...). De-duped list. Helps _photo_vql_ide_window_warning + capture_provenance even on empty VQL (if vdisplay side put hints in nl/cv).
- Logging: candidates log already shows layer_count=0; map now surfaces "map_element_key"; plan keeps full warnings + "used_map_because..." + provenance (map vs observe).

**Still required on user side (vdisplay checkout) for clean run:**
- `pip install -e ".[observe]"` (in the venv running `vdisplay` + `bash koru-*.sh`) + system tesseract-ocr => rich layers + window titles + capture_validation with real "PyCharm ..." in titles.
- Before drive: focus PyCharm on DP-2, make sure titlebar text ".... - PyCharm" is visible (not covered, not Cursor). Run the pre-check `vdisplay screenshot --source DP-2` and inspect output JSON for "window_titles" containing "PyCharm" + capture_validation.capture_confirmed ~true.
- Re-run the exact pre-check + drive + audit block. Expect: elements>0 or (if still no imgl) clean map:prompt (or ai-chat-input) with positive local y ~1000+, no "below_850" warning, inference_ok (or explicit map_on_empty with app_match), capture_confirmed from provenance, submitted=true if --submit, full 4 commands in plan with sane globals.
- If using KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH=1 temporarily for tests, still audit the warnings.

**Next verification (user):**
Re-execute the 3-block commands from the query (with PyCharm truly foreground + title containing "PyCharm"), then audit. Then `git status` + any .vdisplay/2026-06-12/.../drive_result.json will show improved plan (no negative y, map_element_key=prompt or good one, empty_vql note if applicable, inference flags honest).

**Related code:** prepare_photo_vql_for_drive (ide_control + refresh + re-capture loop), perform_photo_vql_focus_and_edit (plan build + actuation guard + submit only on combined_ok), _build_vql_command_plan (inference_ok = validation.ok and mismatch is None), vql_sidecar_is_stale (empty_vql_layers + capture_validation_failed reasons).

This run confirmed that map fallback + pre-interior focus is resilient for "type the prompt" even on 0-layer captures; the fixes make the *audit/log/decision* side honest and prevent bad coord transforms from polluting the plan. Clean VQL (imgl) + confirmed capture remains the path to inference_ok + submit without guards.
