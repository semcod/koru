# Photo-VQL drive — JetBrains/PyCharm na Wayland

**Stan:** 2026-06-12 · **moduł:** `src/koru/integrations/vdisplay_client.py` · **testy:** `tests/test_photo_vql_drive.py`

> **Kalibracja OS injectora** jest w trakcie testów (współrzędne DP-1). Preferowana ścieżka to **vdisplay/photo-VQL**, nie blind click w terminal.

## Podsumowanie

Pętla **observe → decide → act → verify** dla wpisywania promptu do czatu PyCharm przez `vdisplay` + photo-VQL (oraz `coru` / `koru autonomous up`):

| Faza | Co robi | Artefakt sesji |
|------|---------|----------------|
| **Observe** | `prepare_photo_vql_for_drive()` — desktop probe, focus IDE, screenshot, walidacja tytułu okna | `observe/prepare.json`, `observe/capture.png`, `observe/capture.png.vql.json` |
| **Decide** | Wybór targetu VQL / map, opcjonalnie LLM vision (OpenRouter) | `decide/vql_chat_candidates.json`, `decide/vql_chat_target_selected.json` |
| **Act** | Ruch myszy, focus, paste/ydotool, opcjonalnie submit | `act/cursor_positioning.jsonl`, `act/command_plan_*.json`, `act/drive_result.json` |
| **Verify** | OCR po wklejce (`verify_chat_text_visible`) | w `drive_result.json` → `verification` |

**Routing drive (daemon, od 0.1.336+):** `plugin` → **`vdisplay`** → `imgl` → `OS-injector` / `wtype`.

**Kryterium sukcesu:** tekst promptu ląduje w **PyCharm AI Chat**, nie w integrated terminal ani w innym IDE. W logu: `backend=vdisplay` lub `photo-vql`, **nie** samo `backend=os_injector`.

---

## `coru` / `koru auto` — typowy workflow (2026-06-12)

### 1. Venv i env

```bash
cd ~/github/semcod/koru
deactivate 2>/dev/null
source .venv/bin/activate
hash -r

export KORU_AUTOPILOT_INSTANCE=jetbrains
export KORU_VDISPLAY_CONTROL_FALLBACK=1
export KORU_VDISPLAY_SOURCE=DP-1          # monitory: DP-1, HDMI-1
export KORU_VDISPLAY_PREFER_PHOTO_VQL=auto
```

Od **0.1.337** `koru auto --agent-lane jetbrains` na Waylandzie **sam ustawia** powyższe `KORU_VDISPLAY_*`, jeśli nie były w shellu.

**Uwaga venv:** jeśli masz `(venv)` i `(base)` obok `.venv`, usuń lub nie aktywuj starego `venv/` — inaczej `virtual_env_mismatch` w logu (interpreter z `.venv`, a `VIRTUAL_ENV` wskazuje `venv/`).

### 2. Daemon po shutdown

Po `koru autopilot shutdown` drive **nie zadziała**, dopóki nie wystartujesz daemona:

```bash
koru autopilot shutdown          # zatrzymaj stary proces
coru                             # lub: koru auto --agent-lane jetbrains
# albo ręcznie:
KORU_AUTOPILOT_INSTANCE=jetbrains koru autopilot daemon
```

Sprawdź w logu `git_sha` daemona — musi być **z bieżącego checkoutu** (np. `774f774…`), nie stary build sprzed routingu vdisplay-first.

### 3. Przed drive — fokus w chacie IDE

- PyCharm na monitorze **DP-1** (nie terminal z historią `coru` w kadrze).
- Kliknij w **pole AI chat** (mrugający kursor).
- Dopiero potem test:

```bash
koru autopilot drive --ide jetbrains 'probe test'
```

W audit logu (`~/.local/state/koru/autopilot.log`) szukaj:

```
drive: routing via semantic fallback (vdisplay → imgl → keyboard/os_injector)
drive → vdisplay/jetbrains: photo-vql semantic chat
```

Jeśli widzisz tylko `backend=os_injector` — vdisplay odrzucił capture (mismatch) albo daemon był stary.

### 4. OS injector — ostatni fallback (kalibracja w testach)

```bash
task koru:ide-os:calibrate IDE=jetbrains
```

- Kalibruj **klikając w pole czatu IDE**, nie w terminal.
- Przykład poprawnej kalibracji (DP-1): `(2336, 588)` — wcześniejsze `(2323, 2409)` trafiały w terminal.
- `env2llm validation` może ostrzegać o `pointer_display_mismatch` dla innych IDE — to nie blokuje profilu `jetbrains`.

---

## Monitory (tom@nvidia)

| Monitor | Użycie |
|---------|--------|
| **DP-1** | Domyślny `KORU_VDISPLAY_SOURCE` dla JetBrains |
| **HDMI-1** | Primary w GNOME — nie ustawiaj na sztywno, jeśli PyCharm jest na DP-1 |

Starsza dokumentacja odnosiła się do **DP-2** (inny układ biurka). Dostosuj `--source` / env do monitora, na którym **fizycznie** stoi okno PyCharm.

---

## Dlaczego tekst ląduje w terminalu

| Przyczyna | Objaw w logu |
|-----------|----------------|
| Brak pluginu JetBrains | `plugin connected=False`, `plugins: []` |
| vdisplay capture mismatch | `capture_confirmed: false`, potem `backend=os_injector` |
| Stary daemon (bez vdisplay-first) | brak linii `drive → vdisplay/…` |
| Fokus w integrated terminal | `terminal host: integrated`, `wtype` pisze do aktywnego okna |
| Zła kalibracja OS injectora | klik w `(x,y)` terminala zamiast chatu |
| Terminal w kadrze screenshot | terminal pollution w VQL (`KORU_*`, `po clear`, …) |

---

## Zmienne środowiskowe

| Zmienna | Domyślnie (JetBrains + Wayland) | Opis |
|---------|----------------------------------|------|
| `KORU_VDISPLAY_CONTROL_FALLBACK` | `1` (auto przez `koru auto`) | Włącza vdisplay przed keyboard |
| `KORU_VDISPLAY_SOURCE` | `DP-1` | Monitor capture |
| `KORU_VDISPLAY_PREFER_PHOTO_VQL` | `auto` | Photo-VQL gdy capture pasuje do IDE |
| `KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS` | `1` | Mysz + focus przed paste |
| `KORU_AUTOPILOT_INSTANCE` | `jetbrains` | Socket lane |

Guardy i flagi mismatch: tabela w sekcji poniżej (bez zmian semantyki).

---

## One-shot drive (vdisplay script)

Pełna instrukcja: [vdisplay `examples/dev-workflow/README.md`](../../../wronai/vdisplay/examples/dev-workflow/README.md#koru--vdisplay--pętla-autonomiczna-photo-vql).

```bash
cd ~/github/wronai/vdisplay
VDISPLAY_CAPTURE_VALIDATE_IDE=jetbrains vdisplay screenshot --source DP-1

unset KORU_VDISPLAY_DRY_RUN
KORU_SRC=~/github/semcod/koru/src IMGL_SRC=~/github/semcod/imgl \
  bash examples/dev-workflow/koru-drive-photo-vql.sh \
  --ide jetbrains --source DP-1 --prompt "test" --submit

bash examples/dev-workflow/koru-audit-last-session.sh --ide jetbrains
```

---

## Guardy (skrót)

| Flaga | Domyślnie | Znaczenie |
|-------|-----------|-----------|
| `capture_confirmed` | z titlebar VQL | Nie ustawiaj `true` tylko dlatego, że map click się udał |
| `KORU_VDISPLAY_RAISE_ALT_TAB` | on dla jetbrains | Recovery focus przed abort |
| `KORU_VDISPLAY_ALLOW_IDE_MISMATCH` | off | Nie omijaj guardów na produkcji |
| `KORU_VDISPLAY_VERIFY_AFTER_PASTE` | on | OCR po paste |

---

## Terminal pollution

Gdy terminal z `coru` jest widoczny na screenshot, imgl OCR tworzy fałszywe warstwy VQL. **Schowaj terminal z kadru DP-1** albo uruchamiaj `coru` z zewnętrznego tmux/TTY.

---

## Checklist operatora

- [ ] `.venv` aktywny (nie stary `venv/`)
- [ ] Daemon po restarcie z aktualnym `git_sha`
- [ ] `KORU_VDISPLAY_*` ustawione (lub `koru auto` na Waylandzie)
- [ ] PyCharm foreground na DP-1, chat focused
- [ ] `koru autopilot drive --ide jetbrains 'probe test'` → `backend=vdisplay` lub chat widoczny w IDE
- [ ] OS injector skalibrowany w polu chat (fallback)
- [ ] Audit: brak samych wpisów `os_injector` bez próby vdisplay

---

## Pliki

| Ścieżka | Rola |
|---------|------|
| `src/koru/integrations/vdisplay_client.py` | prepare, send_chat, guards |
| `src/koru/integrations/photo_vql_*.py` | validation, target, monitor (refactor CC) |
| `src/koruide/daemon/handlers_drive.py` | routing vdisplay-first |
| `src/koru/autonomous_vdisplay_defaults.py` | auto env na Wayland |
| `tests/test_photo_vql_drive.py` | kontrakt |

---

## Historia

| Data | Zmiana |
|------|--------|
| 2026-06-12 | Doc: coru workflow, DP-1, daemon restart, vdisplay-first routing, kalibracja WIP |
| 2026-06-12 | Kod: auto `KORU_VDISPLAY_*`, doctor vdisplay hint, venv stale label |
| 2026-06-09 | imgl stub fix, guard terminal pollution, focus recovery |
| wcześniej | Photo-VQL + LLM vision, JetBrains corner heuristic |

---

## Zobacz też

- [`autopilot-quickstart.md`](./autopilot-quickstart.md) — sekcja JetBrains/Wayland
- [`autonomy-ide-cursor.md`](./autonomy-ide-cursor.md) — szerszy kontekst autonomii
- [`ide-control-architecture.md`](./ide-control-architecture.md) — fallback chain
