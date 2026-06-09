# Koru — desktop URI, getv i orchestracja MCP

Koru udostępnia **bridge MCP** do `nlp2uri` — ten sam model URI co w całym ekosystemie Semcod/wronai.

> **Uwaga:** `nlp2uri` obsługuje dziś głównie **desktop** (`app://`, `desktop-window://`, getv, SystemMap).
> Sterowanie czatem IDE (drive, plugin, ack) idzie przez **`koruide`**, nie przez nlp2uri.
> Pełna analiza: [`ide-control-architecture.md`](ide-control-architecture.md).
> Plan rozbudowy nlp2uri pod IDE: [`plans/nlp2uri-koruide-integration-refactor-plan.md`](plans/nlp2uri-koruide-integration-refactor-plan.md).

## Instalacja

```bash
cd ~/github/semcod/koru
pip install -e ".[desktop]"    # nlp2uri + env2llm
# pełny stack env + MQTT:
pip install -e ".[envmap]"
pip install -e ~/github/semcod/nlp2uri[envmap]
pip install -e ~/github/semcod/env2llm[mqtt]
pip install -e ~/github/wronai/getv
```

## MCP w Cursor

```json
{
  "mcpServers": {
    "koru": {
      "command": "python",
      "args": ["-m", "koru.mcp_server"],
      "cwd": "/home/tom/github/semcod/koru",
      "env": {
        "NLP2DSL_BACKEND_URL": "http://localhost:8010",
        "GETV_HOME": "/home/tom/.getv"
      }
    }
  }
}
```

Alternatywa: użyj **todomat-mcp** jako jednego routera (zawiera child `nlp2uri-mcp`).

## Narzędzia URI

| Tool | Opis |
|------|------|
| `koru_desktop_uri_plan` | NL → URI + plan OSAction (+ `control_plan` dla intencji IDE) |
| `koru_desktop_uri_handle` | Plan + execute (domyślnie `dry_run: true`); `transport=imgl` dla UI |
| `koru_imgl_execute` | Vision-guided UI (kliknij / wpisz / ctrl+enter) przez imgl |
| `koru_ide_drive` | Wykonanie drive przez koruide (MCP, osobne narzędzie) |
| `koru_ide_control_plan` | NL → `koru.control.v1` plan (IDE intencje) |
| `koru_ide_control_execute` | Plan + execute przez nlp2uri/koruide (dry-run domyślnie) |
| `koru_ide_list_uris` | Live autopilot status → indeks `ide://` / `ide-chat://` |

CLI:

```bash
koru autopilot status --format systemmap
```
| `koru_desktop_uri_list_getv_uris` | Indeks `~/.getv` → `getv://` |
| `koru_desktop_uri_resolve_getv` | NL → `getv://` URI |
| `koru_desktop_uri_get_getv_var` | Metadane zmiennej (masked) |
| `koru_desktop_uri_resolve_system_map` | NL → `command://` / `artifact://` / … |
| `koru_desktop_uri_list_system_uris` | Indeks SystemMapIR |
| `koru_env2llm_get_registry` | Live SystemMapIR (JSON) |
| `koru_env2llm_render_registry` | Render doql/yaml/json/md |
| `koru_env2llm_refresh_registry` | Zapis `environment.*` + MQTT |
| `koru_env2llm_get_desktop` | Okna GNOME / sesja GUI |
| `koru_env2llm_list_commands` | Schematy poleceń z rejestru |
| `koru_env2llm_list_uris` | Indeks nlp2uri nad rejestrem |
| `koru_env2llm_mqtt_status` | Status mostu MQTT |

## Przykłady

### Desktop

```json
{
  "name": "koru_desktop_uri_plan",
  "arguments": { "prompt": "open firefox", "platform": "linux" }
}
```

### IDE chat (control plan)

```json
{
  "name": "koru_desktop_uri_plan",
  "arguments": { "prompt": "wyślij prompt do Cursor w tym projekcie", "platform": "linux" }
}
```

Odpowiedź zawiera `control_plan` (`koru.control.v1`) z `transport=koruide_socket` i `replay.mcp=koru_ide_drive`.
Tekst promptu jest w `plan.spec.metadata.text` / `control_plan.actions[0].text_ref`, **nie** w URI.

Wykonanie: `koru_ide_drive` z `text` z planu, lub CLI z `control_plan.actions[0].replay.cli`.

### Zmienna getv

```json
{
  "name": "koru_desktop_uri_resolve_getv",
  "arguments": { "prompt": "GROQ_API_KEY" }
}
```

### Workflow z DOQL

```json
{
  "name": "koru_desktop_uri_resolve_system_map",
  "arguments": {
    "prompt": "send invoice to client",
    "doql_path": "/home/tom/github/wronai/nlp2dsl/examples/01-invoice/environment.doql.less",
    "fallback_desktop": false
  }
}
```

### Live registry (env2llm)

```json
{
  "name": "koru_env2llm_refresh_registry",
  "arguments": {
    "project_root": "/home/tom/github/semcod/koru",
    "probe_desktop": true,
    "publish_mqtt": true
  }
}
```

```json
{
  "name": "koru_env2llm_list_uris",
  "arguments": { "project_root": "/home/tom/github/semcod/koru" }
}
```

Standalone serwisy env2llm (bez Koru MCP):

```bash
env2llm-serve --project . --mqtt          # REST :8770
env2llm-mqtt bridge --project .           # MQTT retain snapshots
```

## Orchestracja zadań (planfile)

URI bridge uzupełnia — nie zastępuje — workflow ticketów:

```json
{ "name": "koru_list_tickets", "arguments": { "project_root": "/home/tom/github/semcod/koru" } }
{ "name": "koru_run_ticket", "arguments": { "project_root": "...", "ticket_id": "..." } }
```

Typowy flow agenta:

1. `koru_list_tickets` — kolejka prac
2. `koru_desktop_uri_resolve_system_map` — znajdź `command://` dla zadania
3. `koru_run_ticket` — wykonaj refaktor / fix w repo
4. `koru_desktop_uri_handle` — opcjonalnie akcja OS (otwórz IDE, screenshot)

## Python API

```python
from koruapi import desktop_uri, env2llm_registry

if desktop_uri.nlp2uri_available():
    print(desktop_uri.desktop_uri_plan("focus firefox", platform="linux"))
    print(desktop_uri.desktop_uri_list_getv())

if env2llm_registry.env2llm_available():
    print(env2llm_registry.env2llm_get_registry(project_root="."))
    print(env2llm_registry.env2llm_list_uris(project_root="."))
```

## TestQL — warstwa DOM (Playwright DSL)

**Warto dodać** obok nlp2uri/env2llm: wmctrl widzi tylko tytuł okna, TestQL steruje **treścią** (CLICK, ASSERT, NAVIGATE).

| Warstwa | Narzędzie | Zakres |
|---------|-----------|--------|
| Okno / focus | env2llm desktop probe + nlp2uri | `desktop-window://focus` |
| Otwarcie URL / app | nlp2uri | `https://…`, `app://firefox/open` |
| DOM / asercje | **testql** | `NAVIGATE`, `CLICK`, `ASSERT` w `.testql.toon.yaml` |

```json
{
  "name": "koru_testql_run_scenario",
  "arguments": {
    "project_root": "/home/tom/github/semcod/koru/examples/nlp2uri-testql-browser",
    "file_spec": "browser-dom.testql.toon.yaml",
    "dry_run": true
  }
}
```

Przykład dwufazowy: `examples/nlp2uri-testql-browser/` (nlp2uri plan → testql DOM).

## Pełny przewodnik ekosystemu

→ [nlp2uri/docs/orchestration.md](https://github.com/semcod/nlp2uri/blob/main/docs/orchestration.md)
