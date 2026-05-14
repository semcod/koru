# Autonomia koru a Cursor IDE — luka i checklista wdrożeniowa

## Podsumowanie

**Częściowa autonomia `koru autonomous`:** koru potrafi orkiestrować pracę wokół ticketów, planfile i bramek jakości, ale pełna „autonomia agenta” w sensie sterowania IDE jak natywny klient Cursor **nie jest** celem ani stanem obecnym — jest to **świadomie ograniczona** autonomia oparta na tym, co da się zrobić stabilnie bez nieudokumentowanego API producenta IDE.

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
- [ ] **IDE**: VS Code, Windsurf, Cursor, JetBrains albo Zed
- [ ] **Backend wstrzykiwania tekstu**: preferowany plugin VS Code/Windsurf/Cursor; fallback X11 `xdotool`, Wayland `wtype` albo `ydotool`
- [ ] **Clipboard tools**: `wl-clipboard` lub `xclip`, gdy używasz backendu klawiaturowego

### Krok 2: Instalacja koru

- [ ] **Klonowanie repozytorium**: `git clone https://github.com/semcod/koru.git`
- [ ] **Wirtualne środowisko**: `python3 -m venv .venv && source .venv/bin/activate`
- [ ] **Instalacja w trybie editable**: `pip install -e .`
- [ ] **Weryfikacja instalacji**: `koru --help`
- [ ] **Inicjalizacja projektu**: `koru --init` (tworzy `.planfile/`)

### Krok 3: Konfiguracja autopilota

- [ ] **Diagnostyka hosta**: `koru autopilot doctor` i opcjonalnie `koru autopilot setup-host --install`
- [ ] **Instalacja pluginu IDE**: `koru autopilot install-plugin` lub ręczne zbudowanie `.vsix` z `plugins/koru-autopilot-vscode/`
- [ ] **Uruchomienie daemona w terminalu**: `koru autopilot daemon --project "$(pwd)"`
- [ ] **Weryfikacja połączenia**: `koru autopilot status`
- [ ] **Test wstrzykiwania**: `koru autopilot drive 'test prompt'`
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
- [ ] **Test autopilot drive**: `koru autopilot drive 'continue with next ticket'`
- [ ] **Test handoff**: `koru autopilot handoff`
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
- [x] **UX: podgląd kolejki** — `koru autopilot status --json` z listą oczekujących promptów i TTL (czytelne dla operatora).
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
