# Plan: refaktor capture na model providerów + integracja z PipeWire / OBS

Status: **draft**, autor: agent, data: 2026-05-22.

## Postęp 2026-05-22 (popołudnie)

- Phase 0 ✅ — providery rozbite na `src/koruvision/providers/{mss,
  portal_screenshot, grim, cli_tools, portal_screencast}.py` +
  `detector.py`; `capture.py` to fasada nad `capture_one_with_providers`.
- Phase 1 ✅ (kod) — `portal_screencast.py` implementuje pełny flow
  ScreenCast → PipeWire fd → `gst-launch-1.0 pipewiresrc`, ranked na końcu
  fallback chain dla Waylanda (przed nim mss → portal_screenshot → cli_tools).
- Cross-OS Docker testy ✅ — `docker/capture/{Dockerfile,smoke.py,run.sh,
  entrypoint-x11.sh}` plus `tests/test_docker_capture.py`
  (gated `KORU_DOCKER_TESTS=1`). Targety: **headless** (oczekuje 0 providerów,
  status `no-log`), **x11** (Xvfb + xsetroot, mss raportuje czarny ekran,
  cli_tools/scrot łapie 1280×800).
- Naprawione przy okazji testów Dockerowych:
  - scrot 1.x nie nadpisywał istniejącego pliku → dodany flag `--overwrite`
    + `os.unlink(tmp_path)` przed `subprocess.run` dla wszystkich CLI
    (gnome-screenshot, spectacle, scrot, maim).
  - `run_png_command` sprawdza teraz `os.path.isfile(tmp_path)` po
    wywołaniu i zgłasza `{binary} did not write {tmp_path}` zamiast czytać
    pustą zawartość.
- Phase 2 ✅ (kod) — `koru observe providers list|test|reset`, wspólne
  `provider_diagnostics_rows()` / `probe_capture_providers()` w detectorze,
  `/api/mesh/diagnostics` z `ranked_providers[]`, tabela providerów w
  `/grid`, reset `.koru/keys/screencast.session`.
- ScreenCast session reuse ✅ — `.koru/keys/screencast.session`, retry po
  wygasłej sesji, JSON stdout z `payload_b64` (PNG bytes).
- Wayland auto-rank ✅ — `portal_screencast` przed mss (po OBS jeśli
  `probe_obs_reachable()`).
- Phase 3 ✅ (kod) — `obs_websocket.py` (OBS WebSocket v5 przez
  `websockets`), `KORU_OBS_*` w `.env` / dashboard Environment tab.
- Phase 4 ✅ (kod) — `/capture/host` + `POST /api/mesh/browser-upload`,
  `browser_getdisplay` provider, `capture_host.html`, frames tagged
  `provider=browser_getdisplay` in mesh store / grid JSON.
- Posprzątane przy okazji: usunięty martwy moduł `koruvision/capture_fallback.py`
  oraz orchestratory `capture_backend`, `auto_backend_order`,
  `auto_failure_message`, `_fallback_after_mss`, `grab_single_mss`,
  `grab_all_mss` w `capture_mss.py` — wszystko zastąpione przez
  `koruvision.providers.detector`.


Powiązane: [`observation-mesh-plan.md`](./observation-mesh-plan.md),
[`src/koruvision/`](../../src/koruvision), [`src/koruobserve/`](../../src/koruobserve),
[`src/koruapi/dashboard_routes.py`](../../src/koruapi/dashboard_routes.py).

> **Cel:** zamiast utrzymywać własną implementację screen-capture, która w
> 2026 zderza się z Wayland/GNOME-49 security policy, **wybieramy najlepsze
> już-istniejące narzędzie per środowisko** i opakowujemy je w wspólny
> interfejs Providera. Koru pozostaje cienką warstwą orkiestracji — nie
> piszemy własnego XCB/portal/PipeWire stacku od zera.

---

## 1. Streszczenie wykonawcze

Obecny `koruvision/capture.py` ma 6 wbudowanych backendów (mss / portal /
grim / gnome-screenshot / spectacle / scrot/maim) sklejonych
ad-hoc. W praktyce w 2026 na GNOME 49 + Wayland **wszystkie 6 fail-uje**,
bo gnome-shell zniósł publiczne D-Bus `Screenshot API` i blokuje XCB
`GetImage` na root window.

Zamiast łatać każdy backend osobno, robimy 3 ruchy:

1. **Refaktor na model Provider** — każda strategia capture to osobna klasa
   implementująca `CaptureProvider`, autodetekcja best-available w runtime,
   `koru observe providers list/test/install`.
2. **Dodajemy 2 nowe providery oparte o stack systemowy:**
   - **`PipeWireScreenCastProvider`** — wykorzystuje
     `xdg-desktop-portal.ScreenCast` (one-time consent → ciągły strumień)
     + `gstreamer pipewiresrc` (już zainstalowany na każdej współczesnej
     dystrybucji) do dekodowania klatek.
   - **`ObsWebSocketProvider`** — jeśli user ma uruchomione OBS Studio z
     pluginem `obs-websocket` (od OBS 28 built-in), bierzemy klatki przez
     JSON-RPC `GetSourceScreenshot`. User raz daje permission OBS-owi
     przez portal, a my dostajemy nieograniczoną liczbę klatek za darmo.
3. **Provider browserowy (`getDisplayMedia`)** — jako opcja zero-install:
   user otwiera `http://host:8765/capture/host`, klika raz „Share screen",
   przeglądarka strumieniuje `MediaStream` → my zapisujemy PNG co 60 s
   przez WebSocket. Działa wszędzie (Chrome/Firefox), żadnych deps na hoście.

---

## 2. Co dziś boli (`vision.log` z tej maszyny)

```text
no screenshot backend succeeded;
  mss:               all monitors returned black frames (XCB GetImage BadMatch)
  portal Screenshot: response code 2 (interactive consent required per shot)
  grim:              compositor doesn't support wlr-screencopy-unstable-v1
  gnome-screenshot:  Invalid rectangle passed (bug w GNOME 49)
  spectacle/maim:    not installed
  scrot:             empty image
```

Każdy z tych błędów to **inny problem** rozproszony po jednym pliku
(`capture_mss.py`, ~470 linii, wszystkie backendy zlepione). Trudno
dodać 7. backend bez refaktoru — i nie powinniśmy tego robić, dopóki
nie odetniemy się od strategii „jeden plik = wszystko".

---

## 3. Krajobraz dostępnych narzędzi (matryca decyzyjna)

| Narzędzie / API | Platforma | Tryb | Consent | Multi-monitor | Status | Werdykt |
|---|---|---|---|---|---|---|
| `xdg-desktop-portal.ScreenCast` + PipeWire | Linux Wayland (GNOME, KDE, sway) | **stream** | **raz** | tak | stabilne | **PRIORYTET 1** |
| `xdg-desktop-portal.Screenshot` | Linux Wayland | one-shot | **każdorazowo** | nie (osobny call/monitor) | stabilne | fallback (interactive) |
| OBS Studio + `obs-websocket` | Linux/macOS/Windows | stream / on-demand | raz w OBS | tak (sceny) | mainstream | **PRIORYTET 2** (opt-in) |
| Browser `getDisplayMedia` | wszystko | stream | raz w przeglądarce | tak | W3C standard | **PRIORYTET 3** (zero-install) |
| `mss` | X11, macOS, Windows | one-shot | brak | tak | OK na X11 | zostaw dla X11 |
| `grim` | Linux wlroots (Sway/Hyprland) | one-shot | brak | tak | OK | zostaw dla wlroots |
| `gnome-screenshot` | GNOME ≤ 48 | one-shot | brak | nie | **broken na 49** | wyrzucamy |
| `spectacle` CLI | KDE Plasma | one-shot | brak | tak | OK | zostaw dla KDE |
| `scrot` / `maim` | X11 | one-shot | brak | tak | OK | zostaw dla X11 |
| `ffmpeg x11grab` | X11 | stream | brak | tak | OK | tylko ciężkie scenariusze |
| `dxcam` | Windows | stream | brak | tak | szybki | macOS/Windows parity |
| `Quartz CGWindowList` | macOS | one-shot | TCC permission | tak | natywny | macOS parity |

**Wniosek:** dla naszego głównego target-stage (Linux Wayland, 2026) to
**ScreenCast portal + PipeWire** jest jedyną drogą, która daje:
- continuous capture,
- one-time consent zapamiętany w xdg-permission-store,
- działa na wszystkich Wayland compositorach (GNOME, KDE, sway, Hyprland).

---

## 4. Architektura — provider pattern

### 4.1. Nowe granice modułów

```
src/koruvision/
  __init__.py
  capture.py                  # PUBLIC API: VisionFrame, capture_all_monitors, list_monitors
  scaling.py                  # bez zmian
  agent.py                    # bez zmian (tylko źródło frames)
  mesh.py                     # bez zmian
  cli_parser.py               # + flagi --provider, --list-providers

  providers/
    __init__.py               # registry + auto-detect
    detector.py               # policy rank; provider contract owns vdisplay.capture

    mss.py                    # X11 / macOS / Windows native (stary _capture_via_mss_single)
    portal_screenshot.py      # xdg-desktop-portal.Screenshot (interactive)
    portal_screencast.py      # xdg-desktop-portal.ScreenCast + gst pipewiresrc  <- NEW
    obs_websocket.py          # obs-websocket bridge                              <- NEW
    browser_getdisplay.py     # browser MediaStream -> WS                         <- NEW
    grim.py                   # wlroots
    spectacle.py              # KDE
    scrot.py                  # X11 CLI
    macos_quartz.py           # macOS Quartz (lazy import)                        <- future
    windows_capture.py        # Windows (windows-capture / dxcam) (lazy import)   <- future
```

### 4.2. Kontrakt providera

```python
# Public owner: vdisplay.capture
from typing import Protocol, runtime_checkable

@runtime_checkable
class ObservationProvider(Protocol):
    name: str
    needs_consent: bool
    streams: bool  # True = stay-resident, False = one-shot per cycle

    def availability(self) -> ProviderAvailability:
        """Inspect env: installed? compositor matches? consent stored?"""

    def list_monitors(self) -> list[MonitorSpec]:
        """Stable monitor IDs across cycles."""

    def capture_all(self) -> list[VisionFrame]:
        """One cycle (default contract)."""

    def start_stream(self, on_frame: Callable[[VisionFrame], None]) -> StreamHandle:
        """Optional: continuous mode for stream providers."""
```

`ProviderAvailability` zwraca: `available: bool`, `reason: str`,
`install_hint: str`, `consent_url: str | None`. Dashboard pokazuje to
1:1 w `/api/mesh/diagnostics`.

### 4.3. Auto-detekcja (ranking)

`detector.rank_providers(env)` zwraca uporządkowaną listę kandydatów:

```python
def rank_providers(env: CaptureEnv) -> list[CaptureProvider]:
    candidates = []
    if env.user_pref:
        candidates.append(env.user_pref)         # KORU_VISION_PROVIDER=...
    if env.obs_websocket_reachable:
        candidates.append(ObsWebSocketProvider())   # opt-in: user ma OBS
    if env.session == "wayland" and env.portal_screencast_available:
        candidates.append(PortalScreenCastProvider())
    if env.compositor == "wlroots":
        candidates.append(GrimProvider())
    if env.session == "x11":
        candidates.append(MssProvider())
        candidates.append(ScrotProvider())
    if env.desktop == "kde":
        candidates.append(SpectacleProvider())
    if env.session == "wayland":
        candidates.append(PortalScreenshotProvider())  # interactive fallback
    return [p for p in candidates if p.availability().available]
```

`koru observe up` próbuje providery po kolei aż pierwszy zwróci klatkę.
Diagnostyka mówi, **który** zadziałał i dlaczego pozostałe nie.

---

## 5. Plan wdrożenia — fazy

### Faza 0 — refaktor strukturalny (0.5 dnia)

- Rozbicie `capture_mss.py` na osobne moduły w `providers/`.
- Wprowadzenie `CaptureProvider` Protocol + `detector.py`.
- Adapter wsteczny: `capture_all_monitors()` deleguje do
  `detector.rank_providers()[0].capture_all()`.
- Wszystkie obecne testy `tests/test_koruvision_capture.py` muszą przejść
  bez zmian semantyki (migracja API).

**Acceptance:** `pytest tests/test_koruvision_*.py` zielony,
`KORU_VISION_PROVIDER=mss koru vision capture` działa identycznie jak dziś.

---

### Faza 1 — PipeWire ScreenCast provider (**najważniejsza**, 1–2 dni)

**Why:** to **jedyne** rozwiązanie continuous-capture, które działa na
Wayland 2026 bez sandboxa.

**Stack:**
- D-Bus `org.freedesktop.portal.ScreenCast`:
  `CreateSession` → `SelectSources(types=MONITOR)` → `Start` (UI dialog **raz**)
  → otrzymujemy `pipewire_fd` + lista node-ID per monitor.
- `gst-launch-1.0`:
  ```
  pipewiresrc fd=<fd> path=<node_id>
    ! videoconvert
    ! videoscale
    ! video/x-raw,width=W,height=H
    ! pngenc snapshot=true
    ! filesink location=/tmp/koru-mon-N.png
  ```
- Implementacja przez subprocess (`/usr/bin/python3` z dostępem do `gi`),
  nie wciągamy `PyGObject` do venva (lekcja z poprzedniego refaktoru
  `portal_capture.py`).

**Pliki:**
- `src/koruvision/providers/portal_screencast.py` (~250 linii)
- `src/koruvision/providers/_portal_session.py` (zarządzanie D-Bus sesją,
  cache `pipewire_fd` na czas życia procesu)
- `src/koruvision/providers/_gst_frame.py` (jeden frame z pipewiresrc)
- `tests/test_provider_portal_screencast.py` — mock portala, mock subprocess

**Consent UX:** przy pierwszym `koru observe up` GNOME pokazuje dialog
„Select what to share". Po wyborze koru zapisuje session token w
`.koru/keys/screencast.session` — kolejne uruchomienia używają tej samej
sesji bez ponownego dialogu (portal pamięta w
xdg-permission-store).

**Acceptance:**
1. Na czystej maszynie Ubuntu 25.10 GNOME 49 Wayland: `koru observe up` →
   pojedynczy dialog wyboru → klatki z 3 monitorów co 60 s.
2. Restart: `koru observe up` → **bez dialogu**, klatki natychmiast.
3. `KORU_VISION_PROVIDER=portal_screencast` wymusza ten provider.

---

### Faza 2 — `koru observe providers` UX + diagnostics v2 (0.5 dnia)

Nowe komendy:

```bash
koru observe providers list           # tabela: name | available | reason | consent
koru observe providers test [NAME]    # próbuje wszystkie / jeden
koru observe providers install obs    # auto-apt OBS + obs-websocket
koru observe providers consent reset  # czyści session tokens
```

`/api/mesh/diagnostics` dostaje pole `providers[]` z pełną tabelą.
Dashboard pokazuje listę z buttonem „Try again" per provider.

**Pliki:**
- `src/koruobserve/providers_cli.py` (~120 linii)
- update `src/koruobserve/diagnostics.py`: doda `providers` do payload
- update `src/korumesh/grid_template.html`: render tabeli providerów

---

### Faza 3 — OBS WebSocket provider (1 dzień, opcjonalne)

**Why:** użytkownicy power-userzy często już mają OBS uruchomione (do
streamingu/nagrywania). Jeśli mają, koru może **darmowo** dostać klatki
przez `obs-websocket` (built-in od OBS 28).

**Stack:**
- Biblioteka: `obsws-python` (lekka, async-friendly, ~50 KB) — dodajemy
  jako extra `koru[observe-obs]`.
- Wywołania:
  ```python
  req = {"requestType": "GetSourceScreenshot",
         "requestData": {"sourceName": "Display Capture",
                         "imageFormat": "png", "imageWidth": 1920}}
  ```
- Config: `KORU_OBS_URL=ws://127.0.0.1:4455`, `KORU_OBS_PASSWORD=...`
  lub `.koru/config.yaml::observe.obs = {url, password, scene}`.

**Pliki:**
- `src/koruvision/providers/obs_websocket.py` (~180 linii)
- `tests/test_provider_obs.py` z mockiem websocket

**Acceptance:** kiedy OBS jest aktywne i obs-websocket włączone,
`koru observe up` używa OBS jako primary providera (priorytet nad
ScreenCast portal, bo nie ma żadnego dialogu).

---

### Faza 4 — Browser `getDisplayMedia` provider (1–1.5 dnia, opcjonalne)

**Why:** zero-install, działa na każdym OS, idealne dla peerów na
Windowsie/macOS bez chęci instalowania niczego.

**Architektura:**
1. Dashboard ma nową stronę `/capture/host?peer=<id>`.
2. Strona robi `navigator.mediaDevices.getDisplayMedia({video: true})`,
   user klika „Share screen" w przeglądarce.
3. JS robi `requestAnimationFrame` co 60s, rysuje na `<canvas>`,
   `toBlob('image/png')`, wysyła przez WebSocket do `wss://host/mesh/v1/upload`.
4. Serwer Koru przyjmuje PNG → tworzy `VisionFrame` z metadanymi
   z body upload (output, native_width, …).

**Pliki:**
- `src/koruvision/providers/browser_getdisplay.py` (serwer-side: WS handler)
- `src/korumesh/capture_host.html` (klient-side: ~150 linii JS)
- update `src/koruapi/dashboard_routes.py`: nowa trasa `/capture/host`

**Acceptance:** otworzenie strony w Firefox/Chrome + klik „Share" →
klatki widoczne w `/grid` peer-a z tagiem `provider=browser`.

---

### Faza 5 — cross-platform parity (opcjonalne, 0.5 dnia per OS)

- **macOS:** `providers/macos_quartz.py` — `Quartz.CGWindowListCreateImage`,
  lazy import `Quartz` z pyobjc.
- **Windows:** `providers/windows_capture.py` — biblioteka `dxcam` (fast)
  lub `windows-capture` (modern). Extra: `koru[observe-windows]`.

---

## 6. Mapowanie obecny kod → nowa struktura

| Obecnie (po dzisiejszym refaktorze) | Po Fazie 0 | Notatka |
|---|---|---|
| `koruvision/capture.py` (99 l.) | `koruvision/capture.py` (publiczne API, ~50 l.) | tylko fasada |
| `koruvision/capture_mss.py` (~470 l.) | `providers/mss.py` + `providers/portal_screenshot.py` + `providers/grim.py` + `providers/scrot.py` + `providers/spectacle.py` + `detector.py` | każdy ~80–120 l. |
| `koruvision/portal_capture.py` | `providers/portal_screenshot.py` (rename) | bez zmian logiki |
| `koruvision/scaling.py` | bez zmian | reused przez providery |
| `koruobserve/diagnostics.py` | + sekcja `providers[]` w payload | rozszerzenie |

Po Fazie 1 dochodzi `providers/portal_screencast.py` (+ pomocnicze).
Po Fazie 3: `providers/obs_websocket.py`.
Po Fazie 4: `providers/browser_getdisplay.py` + JS klient.

---

## 7. Konfiguracja (`.koru/config.yaml`)

```yaml
observe:
  vision:
    enabled: true
    interval_seconds: 60
    scale: 0.2
    provider: auto                 # auto | mss | portal_screencast | obs | browser | grim
    fallback_chain:                # opcjonalnie nadpisuje default ranking
      - obs
      - portal_screencast
      - mss
    obs:                           # tylko gdy provider in (auto, obs)
      url: ws://127.0.0.1:4455
      password_env: KORU_OBS_PASSWORD
      source: "Display Capture"
    screencast:
      session_token_path: .koru/keys/screencast.session
      monitors: [0, 1, 2]          # opt-in subset, domyślnie wszystko
```

`KORU_VISION_PROVIDER=...` override-uje YAML; CLI flag `--provider`
override-uje env.

---

## 8. Zmiany w testach

| Test | Faza | Co dodajemy |
|---|---|---|
| `tests/test_provider_protocol.py` | 0 | Protocol conformance, registry lookup, monkeypatchable detector |
| `tests/test_provider_mss.py` | 0 | przeniesienie istniejących testów `_capture_via_mss_*` |
| `tests/test_provider_portal_screencast.py` | 1 | mock D-Bus session create/select/start, mock gst-launch subprocess |
| `tests/test_provider_obs.py` | 3 | mock `obsws-python` client |
| `tests/test_provider_browser_upload.py` | 4 | WS handler accept + PNG → VisionFrame |
| `tests/test_observe_providers_cli.py` | 2 | `koru observe providers list/test/install` |

Existing tests (`test_koruvision_*`, `test_korumesh_store`,
`test_serve`, `test_koruobserve_diagnostics`) muszą pozostać zielone
bez modyfikacji.

---

## 9. Co WYRZUCAMY

- `gnome-screenshot` z fallback chain — broken na GNOME 49, `Invalid
  rectangle passed`. Nie warto utrzymywać kodu wokół.
- Bezpośrednie wywołanie `org.gnome.Shell.Screenshot` D-Bus —
  `AccessDenied` od GNOME 49.
- Backend `KORU_VISION_BACKEND=command` jako bulk — rozbity per-tool
  (grim/spectacle/scrot to teraz osobne providery).

---

## 10. Ryzyka i mitygacje

| Ryzyko | Mitygacja |
|---|---|
| Portal `ScreenCast` ma niestabilne API D-Bus w niektórych compositorach | Trzymamy się portal-spec v5 (stabilne od 2024); per-compositor smoke testy w CI mode skipowane gdy brak Wayland |
| `gst-launch` jako subprocess zwiększa latency vs. native bindings | Klatki co 60 s, latency 200–400 ms jest akceptowalna; alternatywnie `python3-gi` jako optional extra dla power userów |
| OBS provider wymaga instalacji OBS — dla wielu userów to nadmiar | Czysto opt-in (kolejność: portal_screencast > obs jeśli ScreenCast działa); diagnostyka pokazuje „OBS nie wykryte, OK" zamiast erroru |
| Browser provider wymaga otwartej karty przeglądarki — kruche | Pozycjonujemy jako opcję dla heterogenicznych peerów; primary stack to portal_screencast |
| Session token w `.koru/keys/screencast.session` może wyciec | perm `0600`, w gitignore, dokumentacja sekcji 7 plan obserwacji |

---

## 11. Definicja sukcesu (acceptance)

1. **Faza 0+1 ukończone:** na tej maszynie (Ubuntu 25.10 GNOME 49 Wayland)
   `koru observe up` → jeden dialog → klatki z 3 monitorów co 60 s w `/grid`.
2. **Faza 2:** `koru observe providers list` pokazuje 7+ providerów z
   `available/reason/install_hint`; `/api/mesh/diagnostics.providers[]`
   z tym samym payloadem.
3. **Faza 3:** z uruchomionym OBS + obs-websocket: provider OBS bierze
   priorytet, klatki bez żadnego dialogu portal.
4. **Faza 4:** dwa peery (Linux + macOS bez instalacji) widoczne na
   jednym dashboardzie przez browser provider.
5. Regix: 0 błędów po każdej fazie (per-provider moduły ≤ 200 l.,
   żaden provider nie podchodzi pod `monolith_collapse`).
6. Zero regresji w istniejących testach — to jest twarda granica.

---

## 12. Co dalej (poza tym planem)

- **AI-driven differential capture:** jeśli klatka N+1 jest 98% identyczna
  do N (sha256 thumbnaili), publikujemy tylko `vision/frame-unchanged`
  envelope — oszczędność JSONL bandwidth.
- **Active-window capture** (osobno od full-monitor) — `xdotool` /
  `kdotool` / portal `Window` w przyszłej spec; dla teraz: pełen monitor.
- **Sandboxed Flatpak build** koru-vision jako fallback dla
  dystrybucji bez portal_screencast — long tail.
