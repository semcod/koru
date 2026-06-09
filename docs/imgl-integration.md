# Integracja Koru z imgl

Koru używa imgl jako **transport wizyjny** — fallback po padnięciu pluginu koruide,
oraz executor UI dla MCP `koru_desktop_uri_handle`.

## Włączenie

**Ważne:** `koru` przełącza się na **koru/.venv** (nie imgl/.venv). Instaluj bridge tam:

```bash
cd ~/github/semcod/koru
bash scripts/install-imgl-bridge.sh
```

Ręcznie:

```bash
cd ~/github/semcod/koru && source .venv/bin/activate
pip install -e . -e packages/koruenv -e packages/coru -e packages/uri2koru \
  -e packages/dsl2koru -e packages/dsl2coru
pip install -e ~/github/semcod/imgl -e ~/github/semcod/imgl/packages/dsl2imgl \
  -e ~/github/semcod/imgl/packages/nlp2imgl
```

REST (gdy bez nlp2imgl lokalnie, port 8219):

```bash
rest2imgl serve --port 8219
export KORU_IMGL_REST_URL=http://127.0.0.1:8219
```

## Zmienne środowiskowe

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `KORU_IMGL_FALLBACK` | `0` | Fallback w `koru auto` po fail pluginu |
| `KORU_IMGL_DESKTOP` | `0` | MCP `desktop_uri_handle` → imgl dla promptów UI |
| `KORU_IMGL_IMAGE` | `/tmp/koru-imgl-screen.png` | Ścieżka zrzutu |
| `KORU_IMGL_WINDOW` | `region-bottom` | Region okna (IDE) |
| `KORU_IMGL_REST_URL` | `http://127.0.0.1:8219` | REST gdy brak nlp2imgl |
| `KORU_IMGL_DRY_RUN` | `0` | Bez wykonania na pulpicie |

## Backend w `koru.yaml`

```yaml
ide_integration:
  default_lane: ide
  lanes:
    ide:
      backend: plugin_socket
      ide: cursor
    vision_fallback:
      backend: imgl
      ide: cursor
```

## Drabina fallbacków (`koru auto`)

```text
koruide plugin socket
  → nlp2uri ide-control (KORU_IDE_CONTROL_VIA_NLP2URI=1)
  → imgl vision (KORU_IMGL_FALLBACK=1)      ← NOWE
  → gillm GuiDriver (KORU_AUTOPILOT_GILLM_FALLBACK=1)
  → os_injector (KORU_OS_INJECTOR_PROFILE)
```

## Shell (nie MCP)

`koru_imgl_execute` to **narzędzie MCP** w Cursorze — nie komenda shell.

```bash
# Koru CLI (po pip install -e . w repo koru)
koru imgl execute "wpisz test w Chat input" --window region-bottom --execute

# dsl2coru UI verbs
dsl2coru exec 'UI_TYPE "hello" IN "Chat input" WINDOW region-bottom'
dsl2coru -c 'UI_KEY ctrl+Return'    # legacy forma
cli2coru exec 'UI_KEY ctrl+Return'  # alternatywa

# Bezpośrednio imgl REST (port 8219, nie 8220=gillm)
rest2imgl serve --port 8219
curl -s -X POST http://127.0.0.1:8219/v1/nl \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"wpisz test w Chat input","window":"region-bottom","execute":true}'
```

## MCP desktop URI

```json
{
  "name": "koru_imgl_execute",
  "arguments": {
    "prompt": "wpisz opisz projekt w Chat input",
    "window": "region-bottom",
    "dry_run": false
  }
}
```

```json
{
  "name": "koru_desktop_uri_handle",
  "arguments": {
    "prompt": "kliknij Projects",
    "transport": "imgl",
    "window": "region-top",
    "dry_run": false
  }
}
```

Włącz auto-routing: `KORU_IMGL_DESKTOP=1` (prompty UI bez jawnego `transport`).

## Verby dsl2coru

```bash
dsl2coru exec 'UI_CAPTURE'
dsl2coru exec 'UI_TYPE "hello" IN "Chat input" WINDOW region-bottom'
dsl2coru exec 'UI_KEY ctrl+Return'
dsl2coru exec 'UI_CLICK "Projects" WINDOW region-top'
dsl2coru exec 'UI_NL "wpisz test w Chat input"'
```

## Pliki

| Plik | Rola |
|------|------|
| `src/koru/integrations/imgl_client.py` | Adapter nlp2imgl / REST |
| `src/koru/agent_backend_runtime.py` | `ImglDesktopBackend` |
| `src/koru/autonomous_cycle_gate.py` | `try_imgl_gui_fallback()` |
| `src/koruapi/desktop_uri.py` | `transport=imgl` |
| `packages/dsl2coru/handlers/ui.py` | Verby `UI_*` |
| `src/koru/control_commands.py` | `imgl_command()` audyt |
