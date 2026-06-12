# Photo-VQL drive — JetBrains/PyCharm na Wayland (DP-2)

**Stan:** 2026-06-09 · **moduł:** `src/koru/integrations/vdisplay_client.py` · **testy:** `tests/test_photo_vql_drive.py` (54 passed)

## Podsumowanie

Pętla **observe → decide → act → verify** dla wpisywania promptu do czatu PyCharm przez `vdisplay` + photo-VQL:

| Faza | Co robi | Artefakt sesji |
|------|---------|----------------|
| **Observe** | `prepare_photo_vql_for_drive()` — desktop probe, focus IDE, screenshot, walidacja tytułu okna | `observe/prepare.json`, `observe/capture.png`, `observe/capture.png.vql.json` |
| **Decide** | Wybór targetu VQL / map, opcjonalnie LLM vision (OpenRouter) | `decide/vql_chat_candidates.json`, `decide/vql_chat_target_selected.json` |
| **Act** | Ruch myszy, focus, paste/ydotool, opcjonalnie submit | `act/cursor_positioning.jsonl`, `act/command_plan_*.json`, `act/drive_result.json` |
| **Verify** | OCR po wklejce (`verify_chat_text_visible`) | w `drive_result.json` → `verification` |

**Kryterium sukcesu (real run):** tekst promptu ląduje w **PyCharm AI Chat** na monitorze DP-2, a nie w Cursorze/terminalu. Audit pokazuje pełną ścieżkę decide/act z uczciwymi flagami (`capture_confirmed`, `inference_ok`, `submitted`).

### Co działa

- Capture portal screencast na DP-2 (2048×1280, rotation=left).
- Map actuation (`pycharm-chat.json`, target `prompt`) przez ydotool + vision — kliki się udają nawet gdy AT-SPI/X11 focus zawodzi.
- Guardy **nie raportują fałszywego `ok: true`** przy mismatch IDE, złym inference lub failed verify.
- `capture_provenance` — osobno od map vs observe; `body_false_positive` gdy OCR widzi „PyCharm” w treści dokumentu Cursora, a nie w titlebarze.
- Prepare **abortuje** gdy foreground = Cursor (domyślnie), z `competing_ide` i hintem.
- **Focus recovery:** przed abortem 1× Alt+Tab + ponowny capture (domyślnie włączone dla JetBrains).
- GNOME Shell raise próbuje wielu needlei (`pycharm`, `intellij`, `jetbrains`, …).
- Audit script pokazuje sekcję **Prepare/observe** + decide/act.

### Główny problem (desktop state)

**Map click ≠ zmiana foreground window w screencast.** Gdy Cursor jest na wierzchu na DP-2:

- `capture_validation.capture_confirmed: false`
- `ide_window_mismatch`, `body_false_positive: true`
- `visual_guard_failed: true`, `confirmation_bias_risk` w `ide_control`
- Drive **poprawnie abortuje** przed `send_chat` (brak paste do złego okna)

AT-SPI / `window_focus` na natywnym Wayland PyCharm często zwraca `ok: false`. Jedyna niezawodna ścieżka to **użytkownik podnosi PyCharm na DP-2** albo Alt+Tab recovery trafia we właściwe okno.

### Terminal pollution (capture contamination)

Gdy terminal z którego uruchamiasz `bash koru-drive-*.sh` jest na tym samym monitorze (DP-2) co capture, imgl OCR czyta historię bash jako warstwy VQL "button/input":

- Objawy: dekada „button/input" z treścią `KORU_VDISPLAY_*`, `DRY_RUN`, `PREFER LLM`, `po clear:`, `audit`, itp.
- Skutki: `ide_window_mismatch` + `capture_confirmed: false` + fałszywe VQL candidates z ujemnym `local_y`
- **Guard:** `_VQL_TERMINAL_LABEL_NOISE` (20+ tokenów) → `-1500` score penalty → odrzut candidates z tokenami shell/env
- **Przed pre-check i drive:** podnieś PyCharm na DP-2, schowaj/zamknij terminal z DP-2 (żeby jego tekst nie był widoczny na zrzucie)

Szczegóły: [`autonomy-ide-cursor.md`](./autonomy-ide-cursor.md) — sekcja "2026-06-12 run analysis (pre-check + drive...)"

### Zasady guardów (2026-06-09)

| Flaga / zachowanie | Domyślnie | Znaczenie |
|--------------------|-----------|-----------|
| `capture_confirmed` | z observe/VQL titlebar | **Nigdy** ustawiane na `true` tylko dlatego, że map click się udał |
| `map_only_fallback` | tylko z `KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH=1` | Można iść map path mimo mismatch; `capture_confirmed` nadal `false` |
| `KORU_VDISPLAY_RAISE_ALT_TAB` | auto **on** dla jetbrains/pycharm/idea | 1× recovery w prepare + 2 cykle w `ensure_vdisplay_ide_control` |
| `KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH=1` | off | Map-only bez potwierdzenia tytułu — tylko testy / awaryjnie |
| `KORU_VDISPLAY_ALLOW_IDE_MISMATCH=1` | off | Szersze zejście z guardów actuation |
| `KORU_VDISPLAY_VERIFY_AFTER_PASTE=1` | on | OCR verify po paste; `ok: false` gdy tekst niewidoczny |

---

## Szybki start (real drive)

Pełna instrukcja krok po kroku: [vdisplay `examples/dev-workflow/README.md`](../../../wronai/vdisplay/examples/dev-workflow/README.md#koru--vdisplay--pętla-autonomiczna-photo-vql).

```bash
cd ~/github/wronai/vdisplay

# 1. Pre-check — tytuł okna MUSI zawierać PyCharm
VDISPLAY_CAPTURE_VALIDATE_IDE=jetbrains vdisplay screenshot --source DP-2
# Sprawdź JSON: capture_validation.capture_confirmed, window_titles

# 2. Upewnij się: PyCharm na wierzchu na DP-2, terminal poza kadrem

# 3. Drive
unset KORU_VDISPLAY_DRY_RUN
KORU_SRC=~/github/semcod/koru/src IMGL_SRC=~/github/semcod/imgl \
  bash examples/dev-workflow/koru-drive-photo-vql.sh \
  --ide jetbrains --source DP-2 --prompt "test" --submit

# 4. Audit
bash examples/dev-workflow/koru-audit-last-session.sh --ide jetbrains
```

### Zmienne środowiskowe (najważniejsze)

| Zmienna | Domyślnie (JetBrains) | Opis |
|---------|----------------------|------|
| `KORU_VDISPLAY_SOURCE` | DP-1 (auto-resolve w prepare) | Monitor capture — użytkownik: `DP-2` |
| `VDISPLAY_CAPTURE_VALIDATE_IDE` | `jetbrains` w drive script | Walidacja tytułu przy screenshot |
| `KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S` | `0.8` | Opóźnienie po focus przed capture |
| `KORU_VDISPLAY_VQL_MAX_AGE_S` | `300` | Maks. wiek sidecara VQL |
| `KORU_VDISPLAY_LLM_VISION_DECISION` | `1` w drive script | LLM refine coords z foto |
| `VDISPLAY_ALLOW_YDOTOOL_TYPING` | `1` | ydotool zamiast clipboard na Wayland |

---

## Interpretacja audit

Sekcja **0. Prepare/observe** (`observe/prepare.json`):

| Pole | Oczekiwane (sukces) | Problem |
|------|---------------------|---------|
| `capture_confirmed` | `true` | `false` → abort lub wymaga ręcznego focus |
| `competing_ide` | brak | `"Cursor"` → Cursor na wierzchu |
| `body_false_positive` | `false` | `true` → „PyCharm” w treści, nie w titlebarze |
| `focus_recovery.ok` | `true` (opcjonalnie) | `false`/brak → Alt+Tab nie pomógł |
| `ide_control.visual_guard_failed` | `false` | `true` → observe ≠ target IDE mimo map click |
| `ide_control_attempts` | 1+ | `1` przy early abort na mismatch |

Sekcje decide/act pojawiają się dopiero po **pełnym** drive (bez abortu w prepare).

---

## Lista zadań

### A. Do sprawdzenia przez użytkownika (real desktop)

- [ ] **PyCharm foreground na DP-2** — titlebar zawiera `- PyCharm` / `PyCharm`, nie `Cursor`.
- [ ] **Terminal poza DP-2** — historia bash nie widać na screenshot (terminal pollution → fałszywe VQL inputy).
- [ ] **imgl zainstalowany** — drive script ustawia `IMGL_SRC` **przed** `KORU_SRC` w `PYTHONPATH`. Koru ma stub `koru/src/imgl` — bez poprawnej kolejności VQL ma 0 warstw (naprawione w `_ensure_real_imgl_on_path` + `_vdisplay_subprocess_env`).
- [ ] **Pre-check przed drive:**
  ```bash
  VDISPLAY_CAPTURE_VALIDATE_IDE=jetbrains vdisplay screenshot --source DP-2 | jq '.capture_validation'
  ```
  Oczekiwane: `capture_confirmed: true`, sensowne `window_titles`.
- [ ] **Pełny drive + audit** — po sukcesie prepare:
  - `decide/vql_chat_target_selected.json` — target z y>850 (composer, nie editor)
  - `act/drive_result.json` — `ok: true`, `submitted: true` (z `--submit`)
  - `verification.verified: true` (jeśli verify włączone)
- [ ] **Map calibration** — jeśli `chat_local_y` < 850 lub ujemne: przekalibruj `maps/pycharm-chat.json` (target `prompt` preferowany nad `ai-chat-input`).

### B. Do poprawy w kodzie (backlog)

- [ ] **Focus bez ręcznego podnoszenia okna** — Alt+Tab recovery jest pierwszym krokiem; rozważyć:
  - wielokrotne cykle Alt+Tab z weryfikacją tytułu po każdym,
  - `wmctrl` / `gdbus` dla konkretnego okna PyCharm (jeśli dostępne na sesji GNOME),
  - dedykowany skrót klawiszowy do PyCharm z mapy okien.
- [ ] **Rozdzielenie actuation od foreground** — map click nie zmienia tego, co widzi screencast; rozważyć krótkie oczekiwanie + re-capture po każdym focus step w `ensure_vdisplay_ide_control`.
- [ ] **Post-paste verify na map path** — upewnić się, że verify OCR działa także gdy target = `map:prompt` (obecnie głównie VQL coords).
- [ ] **Persist `drive_result` w ścieżce ide-prompt** — drive script zapisuje po `send_chat`; ujednolicić w `send_chat()` dla wszystkich backendów.
- [ ] **Dokumentacja vdisplay** — zsynchronizować `docs/guides/autonomy-loop.md` z guardami (sekcja poniżej w koru jest aktualna).
- [ ] **CI / testql** — rozszerzyć scenariusz o testy focus_recovery i `map_only_fallback` (obecnie 16 testów kontraktu w testql).

### C. Znane ograniczenia (nie bugi)

- Native Wayland PyCharm: AT-SPI focus często `false` — map/ydotool to primary path.
- OCR może widzieć nazwę IDE w **treści edytora** (np. plik o PyCharm) — `body_false_positive` chroni przed fałszywym match.
- `KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH=1` pozwala paste mimo Cursor foreground — **niezalecane** na produkcji; audit zostawia `capture_confirmed: false`.

---

## Pliki i ścieżki

| Ścieżka | Rola |
|---------|------|
| `koru/src/koru/integrations/vdisplay_client.py` | prepare, send_chat, guards, photo VQL |
| `koru/src/koru/integrations/autonomy_session.py` | sesje `.vdisplay/YYYY-MM-DD/*__koru-{ide}/` |
| `koru/tests/test_photo_vql_drive.py` | kontrakt testów (49) |
| `vdisplay/examples/dev-workflow/koru-drive-photo-vql.sh` | entrypoint real drive |
| `vdisplay/examples/dev-workflow/koru-audit-last-session.sh` | audit z sekcją prepare |
| `vdisplay/maps/pycharm-chat.json` | kalibracja map DP-2, rotation=left |

---

## Historia zmian (skrót)

| Data | Zmiana |
|------|--------|
| 2026-06-09 (kontynuuj #2) | Fix imgl stub conflict (`koru/src/imgl` vs semcod imgl); `_vdisplay_subprocess_env`; xdotool focus fallback; 54 testy; refresh → 350 warstw VQL |
| 2026-06-12 | Sesje datowane, guard terminal pollution, map target `prompt` first, empty VQL → map fallback |
| wcześniej | Photo-VQL + LLM vision, JetBrains corner heuristic (y>850), enrich capture meta dla rotation |

---

## Zobacz też

- [`autonomy-ide-cursor.md`](./autonomy-ide-cursor.md) — szerszy kontekst autonomii koru + Cursor
- [`wronai/vdisplay/docs/guides/autonomy-loop.md`](../../../wronai/vdisplay/docs/guides/autonomy-loop.md) — pętla vdisplay + layout sesji
- `testql-scenarios/vdisplay-photo-vql-drive.testql.toon.yaml` — kontrakt false-ok guard
