# testql-scenarios — koru

Scenariusze TestQL/OQL dla WUP, `coru calibration` i smoke CI.

**Dokumentacja:** [`docs/llm-tools/testql/README.md`](../docs/llm-tools/testql/README.md) ·
[`docs/autopilot-quickstart.md`](../docs/autopilot-quickstart.md) ·
[`packages/coru/README.md`](../packages/coru/README.md)

## WUP quick / dry-run safe

Uruchamiane przez `wup watch` bez efektów ubocznych (głównie `SHELL … --dry-run`):

| Scenario | Cel |
|----------|-----|
| [`cli-smoke.testql.toon.yaml`](./cli-smoke.testql.toon.yaml) | Podstawowy smoke |
| [`cli-koru.testql.toon.yaml`](./cli-koru.testql.toon.yaml) | `koru --help` |
| [`cli-koru_api.testql.toon.yaml`](./cli-koru_api.testql.toon.yaml) | `koru-api` CLI |
| [`cli-koru_dsl.testql.toon.yaml`](./cli-koru_dsl.testql.toon.yaml) | `koru-dsl` CLI |
| [`cli-koru_wup_testql.testql.toon.yaml`](./cli-koru_wup_testql.testql.toon.yaml) | `koru-wup-testql` |
| [`cli-coru_calibration.testql.toon.yaml`](./cli-coru_calibration.testql.toon.yaml) | `coru calibration --help` |

## Live / manual only

Nie uruchamiaj w WUP quick probe bez świadomej zgody:

| Scenario | Cel |
|----------|-----|
| [`cli-koru-live.testql.toon.yaml`](./cli-koru-live.testql.toon.yaml) | Pełne komendy `koru` (nie dry-run) |
| [`conversations/`](./conversations/) | Scenariusze konwersacyjne E2E |
| `*-desktop-calibration.oql` | Preflight `DESKTOP_*` dla `coru calibration` — **advisory** na Wayland/GNOME |

### Desktop calibration templates (`coru calibration`)

Szablony kopiowane do `.planfile/.koru/calibration-{ide}-desktop.oql`:

| IDE | Template |
|-----|----------|
| cursor | [`cursor-desktop-calibration.oql`](./cursor-desktop-calibration.oql) |
| antigravity | [`antigravity-desktop-calibration.oql`](./antigravity-desktop-calibration.oql) |
| vscode | [`vscode-desktop-calibration.oql`](./vscode-desktop-calibration.oql) |
| windsurf | [`windsurf-desktop-calibration.oql`](./windsurf-desktop-calibration.oql) |

```bash
coru calibration --skip-desktop --skip-bridge   # plugin probe only (zalecane na Wayland)
coru calibration                                 # z opcjonalnym DESKTOP_* preflight
```
