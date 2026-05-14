# Autonomia koru a Cursor IDE — luka i checklista wdrożeniowa

## Podsumowanie

**Częściowa autonomia `koru autonomous`:** koru potrafi orkiestrować pracę wokół ticketów, planfile i bramek jakości, ale pełna „autonomia agenta” w sensie sterowania IDE jak natywny klient Cursor **nie jest** celem ani stanem obecnym — jest to **świadomie ograniczona** autonomia oparta na tym, co da się zrobić stabilnie bez nieudokumentowanego API producenta IDE.

**Autopilot (`koru autopilot`)** to w praktyce **wstrzykiwanie promptów** do czatu IDE (wklejka + submit), a nie pełne API Cursor ani pełna kontrola nad modelem, narzędziami agenta ani cyklem sesji po stronie Cursor. Działa to jak **most terminal ↔ pole czatu**, nie jak headless agent API.

**MCP** w stacku koru jest **osobnym torem** (konfiguracja serwerów MCP, provisioning, integracja z workflow) — nie należy mylić go z autopilotem: MCP rozwiązuje integrację narzędzi z LLM w IDE, ale **nie zastępuje** protokołu odczytu odpowiedzi LLM ani jednolitego kanału shell↔IDE w sensie sterowania agentem.

### Co brakuje do „pełnej” integracji z IDE (Cursor)

| Obszar | Co brakuje (krótko) |
|--------|----------------------|
| **Odczyt odpowiedzi LLM** | Brak niezawodnego, wspieranego oficjalnie sposobu na odczyt treści odpowiedzi modelu z czatu do procesu zewnętrznego (zamknięta pętla bez OCR / hacków). |
| **Sterowanie narzędziami agenta** | Autopilot nie wywołuje narzędzi agenta (edycja plików, terminal IDE) programistycznie — tylko dostarcza tekst do czatu. |
| **Jeden kanał shell ↔ IDE** | Terminal i IDE nie mają jednego spójnego duplexowego kanału zdarzeń (stdout/stderr agenta vs. zdarzenia czatu); są to osobne światy zszywane heurystykami. |
| **Polityka IDE** | Brak centralnej polityki po stronie IDE (np. „czy wolno commitować”, „jakie MCP”, limity tokenów) sterowanej z koru — użytkownik i konfiguracja IDE nadal są źródłem prawdy. |
| **Powiązanie ticketów z sesją** | Ticket w planfile nie jest natywnie „sesją” Cursor; brak twardego ID sesji IDE ↔ PLF-XXX w protokole producenta. |

---

## Lista zadań wdrożeniowych

### Protokół IDE

- [ ] **Zdarzenia `session.ended`** — emitowanie i konsumpcja na kanale socket/NDJSON między daemonem a rozszerzeniem IDE (spójny kontrakt, nie tylko heurystyka czasu).
- [ ] **Read-side odpowiedzi LLM** — prototyp odczytu treści ostatniej odpowiedzi z dokumentu czatu (`openTextDocument(chatUri)` lub równoważnik) z testem integracyjnym na jednym IDE.
- [ ] **Wersjonowanie protokołu** — pole `protocol_version` w każdej ramce NDJSON i test odrzucenia niezgodnych klientów.
- [ ] **Heartbeat / reconnect** — metryka „czas od ostatniego ping” w `koru autopilot status` + automatyczne ponowne podłączenie rozszerzenia po restarcie IDE.

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
- [ ] **Rate-limit `drive`** — max N wiadomości/min na socket per UID z komunikatem błędu i logiem audytowym.
- [ ] **UX: podgląd kolejki** — `koru autopilot status --json` z listą oczekujących promptów i TTL (czytelne dla operatora).

### Testy

- [ ] **Test: pełna ścieżka daemon → mock IDE** — fixture socket + nagranie ramek NDJSON (regresja na limit 1 MiB i typy).
- [ ] **Test: `SO_PEERCRED` odrzuca obcy UID** — asercja na odmowę połączenia przy symulowanym innym UID (gdzie środowisko CI na to pozwala; w przeciwnym razie skip z jasnym powodem).
- [ ] **Test kontraktu planfile** — ticket YAML z sekcją „wynik ostatniego runu” po appendzie — diff złoty vs. wygenerowany.

---

## Zobacz też

- [`autopilot-quickstart.md`](./autopilot-quickstart.md) — jak włączyć autopilota z terminala.
- [`autopilot-roadmap.md`](./autopilot-roadmap.md) — fazy P2+ (m.in. `session.ended`, read-side).
- [`planfile-execution-gateway.md`](./planfile-execution-gateway.md) — plan na bramkę wykonania dla wielu aktorów.
