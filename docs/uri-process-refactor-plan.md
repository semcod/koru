# Plan refaktoryzacji: koru na bazie URI-process (wzorzec ifURI / urivision)

> Status: propozycja (2026-07-05). Kontekst: diagnoza „prompt nie trafia do czatu Qodera”
> pokazała, że sterowanie drive jest imperatywną drabinką ukrytą w kodzie
> (`handlers_drive._route_drive`), nieadresowalną i trudną do wnioskowania przez LLM.
> Cel: każdy krok autonomii jako **atomowy, adresowalny proces URI** z kontraktem wyniku
> (DecisionCard), tanią walidacją przed wykonaniem i zasadą *verify-before-act* —
> jak w `if-uri/urivision` (VURI) i konektorach `urirun-*`.

## 1. Dlaczego (lekcja z incydentu Qoder)

Łańcuch przyczyn, przez który `coru auto` nigdy nie wpisał promptu do czatu Qodera:

1. **Wybór lane jest niejawny.** `TERMINAL_EMULATOR=JetBrains…` → `_jetbrains_terminal_env_hint()`
   (`src/koruide/ide.py:551`, sprawdzane pierwsze w `ide.py:646`) wymusza lane=jetbrains;
   terminal-host bije focused-window i listę działających IDE (`ide.py:919-922`).
   Qoder (pid widoczny w `ides`) nigdy nie staje się celem. Decyzja nie ma śladu
   „dlaczego” w formie danych — tylko log tekstowy.
2. **Cel bez zdolności.** Lane=jetbrains nie ma pluginu (`supports_vscode_extension=False`,
   `koruide/ides/jetbrains.py:63`), adapter nie istnieje (`ide_adapters/registry.py:17-46`),
   a na Waylandzie ślepy injector jest blokowany (`handlers_drive.py:209-232`).
   Ta niewykonalność jest wykrywana **w runtime, po próbie**, zamiast tanio przy walidacji.
3. **Qoder jest wspierany połowicznie.** Jest detekcja i aliasy (`ide.py:30,44-46,59,85,96`)
   oraz instalacja umbrella-VSIX przez CLI (`koruide/plugin_installer.py`), ale:
   brak strategii `qoder` w `koruide/ides/registry.py:58-66`, brak adaptera doctora,
   brak wpisów w słownikach vdisplay (`vdisplay_client.py:674,1092`), a plugin VSIX
   zgłasza się jako `vscode` i szuka `koru-autopilot-vscode.sock` (`socketPath.ts:39-69`),
   nie `koru-autopilot-qoder.sock`. Każdy z tych braków to osobny cichy punkt awarii.

Wniosek architektoniczny: zdolności (target IDE, backend wpisywania, weryfikacja,
polityka) są dziś rozproszone po słownikach, klasach strategii i drabinkach if-ów.
LLM (i operator) nie może ich enumerować, adresować ani walidować przed wykonaniem.

## 2. Wzorzec docelowy (z urivision / ifURI)

Z `if-uri/urivision/README.md` i ekosystemu `urirun-*` przejmujemy cztery zasady:

1. **Wszystko jest URI.** Zdolność = adres (`ide://`, `drive://`, `verify://`,
   `policy://`, `event://`), nie import Pythona. Reużycie przez rezolucję adresu.
2. **Proces = deklaracja, nie kod.** Plik procesu (parser → AST → walidacja → kompilacja
   → runner). Złe procesy blokowane **tanio**, przed dotknięciem IDE.
3. **Kontrakt wyniku = DecisionCard.** Każde wykonanie zwraca decyzję z dowodami
   (`decision: ok|fix|block|unknown`, `confidence`, `findings[]` z evidence,
   `next_actions[]`), wymuszone schematem — nie log tekstowy do grepowania.
4. **Verify-before-act + postcond.** Wzorzec `guarded_batch` z vguard: akcja → weryfikacja
   postconditions (czy tekst wylądował w czacie?) → retry albo eskalacja. Szybkość
   nigdy bez strażnika.

## 3. Model URI dla koru

Proponowane schematy (spójne z `urirun`, do ewentualnego wpięcia w `uri_router`):

| Schemat | Znaczenie | Dziś (kod imperatywny) |
|---|---|---|
| `ide://qoder/chat` | powierzchnia docelowa (IDE + surface) | `pick_target`/`resolve_drive_target` w `ide.py` |
| `lane://auto`, `lane://qoder` | proces wyboru lane z dowodami | `_terminal_ide_from_env_with_source` + merge w `ide_router.py` |
| `drive://qoder/chat/submit` | atomowy proces paste+submit | `handlers_drive.handle_drive/_route_drive` |
| `via://plugin/vscode-vsix`, `via://vdisplay/photo-vql`, `via://imgl`, `via://injector/ydotool` | backendy jako konektory | prywatne `_drive_via_*` |
| `verify://chat/prompt-landed` | postcondition (bubble-db, probe, wizja) | `submit_verify`, `chat_history_watcher` |
| `policy://wayland/no-blind-injector` | polityka jako dane | `_blind_keyboard_fallback_blocker` (`handlers_drive.py:209`) |
| `ticket://planfile/STARTER-567` | jednostka pracy | `planfile_queue` |
| `event://koru/drive/<corr>` | ślad wykonania | logi OBS (`corr=`, `interface_id=`, `transport=`) — już prawie to robią |
| `llm://openrouter/<model>` | model do wnioskowania/wizji | tillm/photo-VQL |

Przykładowy proces `.kuri` (analogiczny do `.vuri`):

```txt
proc    drive://qoder/chat/submit
target  ide://qoder/chat
use     via://plugin/vscode-vsix prefer, via://vdisplay/photo-vql fallback
input   ticket://planfile/STARTER-567 as prompt/text
require policy://wayland/no-blind-injector, policy://drive/verify-before-act
act     paste+submit
verify  verify://chat/prompt-landed timeout=8s retries=2
emit    artifact://reports/drive/STARTER-567.decision.json as schema://koru/drive-card.v1
trace   event://koru/drive
```

Walidator odrzuca ten proces **przed wykonaniem**, jeśli: target nie ma żadnego
dostępnego `via://` (np. plugin niepodłączony i vdisplay nieskalibrowany dla tego
źródła), albo polityka wyklucza jedyny pozostały backend (Wayland + blind injector).
To jest dokładnie klasa błędu z incydentu — dziś wykrywana po 3 nieudanych próbach
i 900 s snu, docelowo w milisekundach przy kompilacji.

## 4. Kontrakt wyniku: DriveCard v1 (odpowiednik DecisionCard)

```json
{
  "decision": "ok | fix | block | unknown",
  "confidence": 0.0,
  "target": "ide://qoder/chat",
  "via": "via://plugin/vscode-vsix",
  "findings": [
    {"aspect": "aspect://drive/focus", "severity": "blocker",
     "evidence": "chat input probe length 0 after paste", "recommendation": "..."}
  ],
  "verified": {"prompt_landed": true, "method": "verify://chat/bubble-db"},
  "next_actions": ["uri": "via://vdisplay/photo-vql", "reason": "plugin timeout"],
  "trace": "event://koru/drive/cli-drive-149685-..."
}
```

Wymuszany schematem (structured output przy krokach LLM; pydantic przy krokach
deterministycznych). Decision engine i autonomous cycle konsumują **karty**, nie
parsują logów. `verdict: no_change (confidence=0.10)` z dzisiejszej pętli staje się
polem karty, z dowodami zamiast zgadywania.

## 5. Fazy

### Faza 0 — taktyczne odblokowanie Qodera (niezależne od refaktoru, 1-2 dni)

> Status 2026-07-05: punkty 1-3 i 5 **wdrożone** (strategia `koruide/ides/qoder.py`,
> adapter, słowniki vdisplay, strategia TS `plugins/koru-autopilot-vscode/src/ides/qoder.ts`,
> równoważność vscode↔qoder w `plugin_router`, `qoder` w zbiorach autonomii/mcp/operatora;
> VSIX 0.2.9 zbudowany i zainstalowany w Qoderze). Punkt 4 (degradacja hinta terminala,
> gdy cel nie ma wykonalnego `via://`) — otwarty; częściowo pokryty istniejącą
> auto-korektą `_STALE_NONPLUGIN_LANES` w `config_startup.py`, która po dodaniu qoder
> do `_AUTOPILOT_PLUGIN_LANES` może już wybrać Qodera przy terminalu JetBrains.

1. Strategia `qoder` w `koruide/ides/` (fork rodziny vscode, wzór: `windsurf.py`)
   + rejestracja w `koruide/ides/registry.py` i `ide_adapters/registry.py`
   (naprawia „no adapter for ide=qoder”). ✅
2. Wpisy `qoder` w `vdisplay_client.py` (`_IDE_PROCESS_PATTERNS`, `_IDE_WINDOW_TITLE_TOKENS`). ✅
3. Socket handshake: plugin VSIX musi próbować socketu per-host-IDE (wykrycie, że
   hostem jest Qoder — `vscode.env.appName`), nie tylko `koru-autopilot-vscode.sock`;
   dodatkowo daemon traktuje vscode↔qoder jako rodzinę równoważną dla starszych
   buildów pluginu. ✅
4. Lane auto: gdy terminal-host IDE nie ma żadnego wykonalnego `via://`, a inne
   działające IDE ma (Qoder z podłączonym pluginem) — degraduj hint terminala i
   wybierz wykonalny cel, z jawnym logiem decyzji. (To już jest zalążek reguły
   „walidacja zdolności przed wyborem celu” z fazy 2.)
5. Dokumentacja operatora: `KORU_AUTOPILOT_IDE=qoder KORU_AUTOPILOT_INSTANCE=qoder`,
   `koru autopilot install-plugin --ide qoder`, weryfikacja `koru autopilot drive --ide qoder 'probe test'`. ✅

### Faza 1 — kontrakty i ślad (2-3 tygodnie, bez zmiany zachowania)

1. Moduł `koru.uri` (albo zależność na `uricore`/`uri_router` z if-uri, jeśli ma być
   współdzielony): parsowanie/rezolucja adresów, rejestr schematów.
2. `schema://koru/drive-card.v1` + zwracanie DriveCard z każdego `_drive_via_*`
   (adapter na istniejące wyniki; stare logi zostają).
3. `event://` trace store: formalizacja istniejących logów OBS (mają już `corr`,
   `interface_id`, `transport`, `replayable`) do append-only JSONL adresowanego URI;
   `koru replay` czyta z tego samego śladu.
4. Testy kontraktowe: każdy backend drive musi zwrócić poprawną kartę w każdym
   terminalnym stanie (sukces, odmowa, timeout) — koniec z ciszą przy porażce.

### Faza 2 — atomizacja drive na procesy URI (3-4 tygodnie)

1. Rozbić `handlers_drive._route_drive` na atomy: `resolve-target`, `select-via`,
   `paste`, `submit`, `verify`, `escalate` — każdy jako proces z wejściem/wyjściem-kartą.
   **Uwaga na klasę regresu z ekstrakcji:** patch-targety late-bindować przez fasadę
   (`handlers_drive` zostaje fasadą delegującą), zgodnie z lekcją z 2026-07-03.
2. Drabinka strategii jako **dane** (`drive-ladder.kuri` per IDE), nie kod: kolejność
   `via://`, warunki, polityki. Polityka Wayland/blind-injector przenosi się z
   `_blind_keyboard_fallback_blocker` do `policy://` ewaluowanej przy kompilacji.
3. Walidator procesów (odpowiednik `validators.validate` z urivision): wykonalność
   celu, dostępność backendów, zgodność kalibracji (mapa HDMI-1 vs źródło DP-1 —
   drugi realny błąd z incydentu — łapany tu), budżet czasu.
4. `verify://` jako pierwszoklasowy krok z postcond+retry (wzorzec `guarded_batch`):
   po każdym paste/submit weryfikacja, że prompt wylądował (bubble-db / probe / wizja),
   zanim cykl uzna drive za wykonany.

### Faza 3 — LLM nad atomami (2-3 tygodnie)

1. Decision engine czyta karty i ślad `event://`, a **wybiera następny proces URI**
   (nie „retry/skip” na stringach). Przestrzeń akcji = enumerowalne adresy z rejestru.
2. Kroki percepcyjne (photo-VQL) jako procesy VURI: `inspect image for aspect://ide/chat-focus`
   → DecisionCard; reużycie `urivision` zamiast własnej ścieżki wizji.
3. Kompilacja promptów z procesu + `aspect://` (jak `compiler.compile_prompt`):
   LLM dostaje pytanie decyzyjne i schemat, nie zrzut logów.
4. Budżety i polityki jakości per proces (`policy://vision/no-guessing`,
   `policy://drive/max-attempts-3`).

### Faza 4 — autonomous cycle jako orkiestracja procesów (3-4 tygodnie, przyrostowo)

1. Cykl scan→queue→drive→verify wyrażony jako sekwencja procesów URI; checkpoint
   (`autonomous_checkpoint`) = pozycja w śladzie `event://` (naturalny replay/resume).
2. Kolejka operatora: blokery jako karty z `next_actions[]` będącymi wykonywalnymi
   URI (dashboard renderuje przyciski z adresów — częściowo już tak działa przez
   `koru replay '...'`).
3. Wygaszenie zdublowanych modułów `autonomous_cycle_*` w miarę przenoszenia logiki
   do procesów; fasady zostają do końca deprecation window.

## 6. Ryzyka i zasady migracji

- **Fasady + late-binding obowiązkowo** przy każdej ekstrakcji (regres 2026-07-03
  uderzył 2× w coru/cli i readiness). Testy patchujące stare ścieżki muszą przechodzić.
- **Żadnej fazy „big-bang”**: DriveCard najpierw jako adapter na istniejące wyniki;
  drabinka-jako-dane najpierw dla jednego IDE (qoder — świeży, najmniej obciążony
  legacy), potem cursor/vscode.
- **Zależność od if-uri**: decyzja architektoniczna — vendorować mini-rezolwer URI
  w koru czy zależeć od `uricore`/`urirun`. Rekomendacja: zacząć od wewnętrznego
  `koru.uri` z API zgodnym z uricore, żeby scalenie było mechaniczne.
- **Wydajność**: percepcja wg lekcji z vguard — batch + jeden capture/OCR na cykl
  weryfikacji, crop-region gdzie dostępny; nigdy szybkość bez postcond.

## 7. Miary sukcesu

- Incydent klasy „Qoder”: wykrycie niewykonalności celu < 1 s (walidacja), z kartą
  `block` + `next_actions` zamiast 3 prób × 900 s sleep.
- 100% terminalnych stanów drive kończy się poprawną DriveCard (test kontraktowy).
- Decision engine: decyzje wybierane z enumerowalnej przestrzeni URI; confidence
  z dowodów, nie heurystyk na logach.
- Liczba modułów `autonomous_cycle_*` maleje; drabinki strategii są plikami danych
  diffowalnymi w PR.
