# Koru autopilot: izolacja między IDE (granice i hardening)

Ten dokument opisuje, jak izolacja działa dzisiaj w praktyce, dlaczego nie jest absolutna oraz jak skonfigurować środowisko, żeby uniknąć przenikania sygnałów między różnymi IDE.

## TL;DR

- Izolacja w Koru jest lane/socket-aware, ale nie jest pełnym sandboxem per IDE.
- Logika środowiskowa została wyodrębniona do pakietu `koruenv` (CLI: `koruenv`).
- Kod wydzielonej paczki znajduje się w `packages/koruenv` (gotowy do niezależnego rozwijania/publikacji).
- Canonical source i testy są utrzymywane wyłącznie w `packages/koruenv`.
- Główne granice izolacji: wybór lane (`KORU_AUTOPILOT_INSTANCE`), socket (`KORU_AUTOPILOT_SOCKET`), dopasowanie pluginu po `ide` i `workspaceFolders`.
- Główne miejsca bez pełnej izolacji:
  - fallback do współdzielonego socketu `koru-autopilot.sock`,
  - współdzielony strumień zdarzeń chat w jednym pliku NDJSON,
  - dziedziczenie/env drift w shellach uruchamianych z różnych IDE.

## Jak to działa w praktyce

### 1) Wybór lane i socketu

Daemon i plugin ustalają kanał komunikacji po unix socket:

- Python: `src/koruide/socket.py` (`default_socket_path`)
- Plugin VS Code-family: `plugins/koru-autopilot-shared/src/socketPath.ts`

Jeżeli nie ustawisz jawnie lane/socket, system może użyć ścieżki domyślnej (singleton), którą łatwo współdzielić między procesami z różnych IDE.

### 2) Router pluginu (ide + workspace)

Daemon wybiera klienta pluginu przez `PluginRouter`:

- `src/koruide/plugin_router.py`
- selekcja bierze pod uwagę `ide`, a gdy dostępne, także `workspaceFolders`.

To ogranicza pomyłki między oknami, ale nie tworzy twardej separacji procesowej.

### 3) Zdarzenia chat są współdzielone

Zdarzenia pluginowe (`message.sent`, `message.received`, `session.*`) trafiają do jednego pliku:

- zapis: `src/koruide/daemon/handlers_plugin_event.py` (`_event_path`, `_append_event`)
- odczyt: `src/koruide/chat_history.py` (`default_events_path`, `read_events`)

Domyślnie to jest jeden plik na hosta/użytkownika (`$XDG_RUNTIME_DIR/koru-autopilot-events.ndjson`).

### 4) Skip/redrive opiera się na aktywności chat

Autonomia używa tych eventów do decyzji cooldown i redrive:

- `src/koru/autonomous_cycle_chat_activity.py`
- `src/koru/autonomous_cycle_chat_activity_analyzer.py`

Jeśli lane/ide nie są precyzyjnie ustawione, aktywność z innego IDE może wpłynąć na decyzje pętli.

## Dlaczego nie ma pełnej izolacji

### 1) Kompatybilny fallback do singleton socketu

Wtyczki VS Code-family mają candidate listę, która obejmuje:

- socket lane (`koru-autopilot-<ide>.sock`),
- oraz socket singleton (`koru-autopilot.sock`).

To pomaga w kompatybilności i migracji, ale zwiększa ryzyko przypadkowego współdzielenia kanału.

### 2) Jeden daemon może obsługiwać wielu klientów plugin

Daemon jest brokerem, nie osobnym procesem per IDE. Routing jest logiczny (ide/workspace), nie twardo odizolowany przez namespace/proces.

### 3) Wspólny log zdarzeń chat

Event store NDJSON jest współdzielony, więc izolacja opiera się na filtrach (np. `ide=`), a nie na fizycznie osobnym strumieniu per lane.

### 4) Env drift między shellami IDE

Uruchamianie Koru z terminali zintegrowanych różnych IDE bez jawnego resetu env może przenosić stare wartości `KORU_AUTOPILOT_INSTANCE`/`KORU_AUTOPILOT_IDE`.

## Co widziałeś w logu i czemu to jest spójne z architekturą

Z podanych logów:

- drive był kierowany do `ide=windsurf` i ack był poprawny (`verification=strict`),
- później pojawiło się `plugin hello accepted: ide=vscode`.

To oznacza, że ten sam broker widział połączenia pluginów z dwóch lane/IDE i normalnie je przyjął. To nie musi oznaczać błędu routingu dla konkretnego drive, ale pokazuje brak pełnej izolacji na poziomie procesu i event stream.

## Hardening: konfiguracja, która realnie separuje lane

### 1) Ustaw unikalny lane i socket per IDE okno

W KAŻDYM shellu, zanim uruchomisz `koru on` / `koru autonomous up`:

```bash
export KORU_AUTOPILOT_INSTANCE=windsurf-main
export KORU_AUTOPILOT_SOCKET="$XDG_RUNTIME_DIR/koru-autopilot-windsurf-main.sock"
export KORU_AUTOPILOT_IDE=windsurf
```

Analogicznie dla drugiego IDE, ale z inną nazwą instance/socket.

Możesz też użyć gotowego helpera, który zawsze ustawia spójny zestaw env:

```bash
pip install -e ./packages/koruenv

# wygeneruj exporty dla bieżącego shella
eval "$(koruenv env windsurf windsurf-main)"

# uruchom pojedynczą komendę już w przypiętym lane
koruenv run windsurf windsurf-main -- koru autopilot daemon --project .
```

Albo załaduj skróty do shella (najwygodniejsze na co dzień):

```bash
source scripts/koru-autopilot-lanes.sh
lane:windsurf
lane:status
lane:run -- koru autopilot drive --ide windsurf --require-plugin "probe"
```

`scripts/koru-autopilot-lane.sh` jest cienkim wrapperem, który wymaga
zainstalowanego `koruenv` i nie fallbackuje już do modułu repo.
Dedykowany CI dla paczki: `/.github/workflows/koruenv-ci.yml`.

### Windows / PowerShell

Na Windows używaj tego samego CLI, ale generuj env w formacie PowerShell:

```powershell
koruenv env vscode vscode-main --shell powershell | Invoke-Expression
koruenv status vscode vscode-main
koruenv run vscode vscode-main -- koru autopilot status --explain
```

Domyślny socket lane na Windows jest rozwiązywany do katalogu tymczasowego
(`LOCALAPPDATA`/`TEMP`) zamiast `/tmp`.

### 2) Przed startem sprawdź aktywny daemon i pluginy

```bash
koru autopilot status --explain
```

Zweryfikuj:

- `socket` wskazuje lane, którego chcesz użyć,
- `plugins[].ide` i `plugins[].workspaceFolders` odpowiadają bieżącemu repo,
- brak nieoczekiwanych pluginów z innych lane.

### 3) Dla trybu shell-only wyłącz autopilot drive

Jeśli sesja ma działać wyłącznie przez stdio/API (bez wklejania do chat IDE), uruchamiaj bez autopilota albo w headless policy:

```bash
koru autonomous up --no-autopilot
```

Lub wymuś policy headless w tym shellu:

```bash
export KORU_HEADLESS=1
```

### 4) Ogranicz cross-lane wpływ eventów chat (opcjonalnie)

Jeśli nie chcesz, by automatyka interpretowała eventy chat:

```bash
export KORU_LLM_REFLECT=0
export KORU_AUTOPILOT_CHAT_INTAKE_TICKET=0
```

To zmniejsza automatyczne reakcje na `message.sent`/`message.received`.

### 5) Osobne profile shella per IDE

Najbezpieczniej: aliasy/skrypty startowe per lane (np. `koru-windsurf`, `koru-jetbrains`) ustawiające komplet env, zamiast ręcznego przełączania.

## Cursor-only (bez Windsurf)

Jeśli pracujesz wyłącznie w Cursorze, a logi / diagnostyka nadal wspominają Windsurf:

1. **Nie polegaj na domyślnym lane w `coru`** — komendy bez nazwy IDE (np. `coru start refaktoryzacje`) wcześniej domyślnie ustawiały `windsurf` / `windsurf-main`. Używaj jawnego lane albo ustaw env w shellu Cursora.
2. **Odśwież wygenerowany lane projektu** — `.planfile/.koru/shell-env.sh` z `koru --init` może nadal eksportować `KORU_AUTOPILOT_IDE=windsurf` mimo obecności `.cursor/`:

```bash
koru --init-agent-lane --agent-lane cursor
source .planfile/.koru/shell-env.sh   # opcjonalnie w zewnętrznym terminalu
```

3. **Ustaw env per sesję Cursor** (zalecane przed `coru` / `koru autonomous up`):

```bash
export KORU_AUTOPILOT_IDE=cursor
export KORU_AUTOPILOT_INSTANCE=cursor-main
export KORU_AUTOPILOT_SOCKET="$XDG_RUNTIME_DIR/koru-autopilot-cursor-main.sock"
```

Albo jednorazowo:

```bash
eval "$(koruenv env cursor cursor-main)"
coru auto cursor cursor-main
```

4. **Wyrównaj socket w workspace** — Cursor czyta `.cursor/settings.json`, nie `.vscode/settings.json`. Stary wpis `koruAutopilot.socketPath` z Windsurf w `.vscode/` nie naprawia mostka Cursor:

```bash
koru ide doctor --ide cursor --fix
```

5. **Sprawdź przed startem**:

```bash
koru autopilot status --explain
koru ide doctor --ide cursor
```

Oczekiwane: `ide=cursor`, socket `koru-autopilot-cursor-main.sock` (lub `koru-autopilot-cursor.sock` gdy instance=`cursor`), brak błędów pluginu Windsurf.

## Minimalny checklist operacyjny

1. Ustaw `KORU_AUTOPILOT_INSTANCE`, `KORU_AUTOPILOT_SOCKET`, `KORU_AUTOPILOT_IDE` jawnie.
2. Sprawdź `koru autopilot status --explain` przed każdym `koru on`.
3. Nie używaj wspólnego singleton socketu dla wielu IDE lane.
4. Dla shell-only używaj `--no-autopilot` lub `KORU_HEADLESS=1`.
5. Gdy lane się pomieszał: restart daemona dla konkretnego socketu i reconnect pluginu tylko w docelowym IDE.

Pomocniczo:

```bash
scripts/koru-autopilot-lane.sh status windsurf windsurf-main
```

## Rekomendowany kierunek produktu (docelowo)

Żeby domknąć izolację architektonicznie, docelowo warto:

1. Przenieść event store z jednego globalnego pliku na pliki per lane/socket.
2. Dodać tryb `strict-lane`, który wyłącza singleton fallback socketu.
3. Wymagać lane-id w plugin hello + twarde odrzucanie mismatch lane po stronie daemona.
4. Domyślnie filtrować wszystkie decyzje chat activity po lane-id, nie tylko po `ide`.
