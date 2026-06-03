# ADR KIDE-001 — granice `koru` vs `koruide`

- Status: Proposed
- Date: 2026-05-16
- Related TODO: `KIDE-001`, `KIDE-002`, `KIDE-003`

## Kontekst

`koru` zawiera dziś zarówno warstwę orkiestracji (queue, scan, planfile, autonomy),
jak i warstwę sterowania IDE (`src/koru/autopilot/*`: protocol, daemon, client,
ide detection, injectors, plugin installer, host setup, audit).

To powoduje:

- zbyt wysoki coupling modułów autonomii i IDE transport/injection,
- trudniejszą ewolucję API komunikacji z IDE,
- większe ryzyko regresji przy zmianach low-level (X11/Wayland/plugin path),
- brak czystej granicy do uruchamiania control-plane na innym hoście/systemie.

## Problem

Potrzebna jest jednoznaczna granica odpowiedzialności, aby:

1. wydzielić komunikację i sterowanie IDE do osobnej paczki `koruide`,
2. zostawić w `koru` tylko use-case orchestration,
3. standaryzować API tak, by klient `koru` był niezależny od implementacji backendu.

## Decyzja

### 1) Podział odpowiedzialności

| Obszar | Właściciel | Uwagi |
| --- | --- | --- |
| Queue/autonomy/scan/gates/context/policy | `koru` | bez zmian domenowych |
| Routing trybu (`headless` vs `ide_shell`) | `koru` | decyzja biznesowa procesu `koru` |
| Wire protocol (`hello/drive/status/ack/error`) | `koruide` | kontrakt transportowy |
| Daemon/control server (UDS, później remote) | `koruide` | control-plane IDE |
| IDE discovery/focus (`ide.py`) | `koruide` | platform-specific |
| Keyboard/OS injectors (`injector.py`, `os_injector.py`) | `koruide` → PyPI **`gillm`** (`gillm.injection.*`) | platform-specific; unit tests w `gillm/tests/` |
| Plugin install / host setup / audit | `koruide` | operacje środowiskowe |
| Kompatybilność legacy autopilot | `koru` + `koruide` | przejściowo przez shimy |

### 2) Zasada integracji

`koru` używa wyłącznie interfejsu klienta `IDEControlClient`.

- Dozwolone: import warstwy klienta/adaptora.
- Niedozwolone: bezpośrednie importy low-level (`daemon`, `injector`, `protocol`, `os_injector`, `ide`) poza adapterem.

### 3) Granica API

`koruide` definiuje i utrzymuje API control-plane (v1 kompatybilne, v2 docelowe).

`koru` traktuje to API jako kontrakt zewnętrzny, z fallbackiem przez `legacy` backend
w trakcie migracji (`KORU_IDE_BACKEND=legacy|koruide`).

## Zakres migracji modułów

Docelowo do `koruide` przechodzą moduły:

- `protocol`
- `daemon`
- `client`
- `ide`
- `injector`
- `os_injector`
- `plugin_installer`
- `host_setup`
- `audit`

Po stronie `koru` pozostają:

- warstwa orkiestracji i decyzji biznesowych,
- interfejs `IDEControlClient` + adaptery,
- cienkie komendy CLI/fasada delegujące do klienta.

## Konsekwencje

### Korzyści

- Czysta separacja orchestrator vs IDE control-plane.
- Stabilny kontrakt API dla wielu środowisk i hostów.
- Lepsza testowalność (testy kontraktowe klienta).
- Mniejsze ryzyko regresji przy zmianach platformowych.

### Koszty

- Krótkoterminowy koszt migracji importów i testów.
- Konieczność utrzymania dual-path (`legacy` + `koruide`) do czasu stabilizacji.
- Dodatkowa złożoność wersjonowania API.

## Guardrails wdrożenia

1. Najpierw interfejs klienta i adapter legacy, potem ekstrakcja modułów.
2. Każdy krok objęty testami kontraktowymi klienta.
3. Brak zmian semantyki CLI bez flagi feature toggle.
4. Zachowana kompatybilność `API v1` do czasu zamknięcia canary rollout.

## Kryteria akceptacji (KIDE-001)

- Istnieje tabela ownership modułów (`koru` vs `koruide`).
- Jawnie zapisana zasada: `koru` używa tylko `IDEControlClient`.
- Zakres migracji modułów autopilot jest wymieniony i spójny z TODO.
- Guardrails określają kolejność i bezpieczeństwo migracji.
