# korudsl & koruapi

Sibling packages in the same wheel as `koru` / `koruide` (under `src/`).

## korudsl — bidirectional scenario DSL

| Direction | CLI |
|-----------|-----|
| DSL → library JSON | `koru dsl to-library scenario.dsl` |
| library → DSL | `koru dsl to-dsl library.json` |
| Round-trip | `koru dsl roundtrip scenario.dsl` |

```python
from korudsl import normalize_dsl_to_library, library_to_dsl, dsl_roundtrip_report
```

## koruapi — all integration surfaces

### Catalog & invoke (CLI)

```bash
koru api list
koru api invoke scan.apply --method dry_run --body '{}'
koru api invoke dsl.to_library --body '{"dsl":"GOAL: t\nSET x=1\n"}'
koru api invoke gate.regix --body '{"command":"task quality:regix:local"}'
```

### HTTP integration API (port **8790**)

```bash
koru api http --project .
# alias: koru api serve

curl http://127.0.0.1:8790/api/v1/integrations
curl -X POST http://127.0.0.1:8790/api/v1/invoke \
  -H 'Content-Type: application/json' \
  -d '{"integration_id":"planfile.tickets","project":"."}'
```

### Dashboard, MCP, local hub (moved under koruapi)

| Legacy | koruapi CLI | Port |
|--------|-------------|------|
| `koru serve` | `koru api dashboard` | 8765 |
| `koru mcp-serve` | `koru api mcp` | stdio |
| `koru local-serve` | `koru api local` | 18766 |

`koru serve` / `koru mcp-serve` / `koru local-serve` remain as **shims** → `koruapi`.

#### Dashboard internals (modules)

The `koru serve` dashboard was split out of one ~1800-line monolith into
four cooperating modules so that the HTTP server, the per-route handlers,
the binding/port-replacement logic, and the page template each evolve
independently:

| Module | Role |
|--------|------|
| [`koruapi/dashboard_serve.py`](../src/koruapi/dashboard_serve.py) | Public surface: `ServeConfig`, `serve()`, `start_serve_background()`, `bind_serve_server()`, `build_server()`, `read_serve_endpoint()`, `write_serve_endpoint_file()`. Owns the `serve_forever` / `KeyboardInterrupt` lifecycle and the `_BoundDashboard` summary that `serve` and `start_serve_background` share. |
| [`koruapi/dashboard_serve_utils.py`](../src/koruapi/dashboard_serve_utils.py) | Port-locking helpers (`_address_in_use`, `_listener_pids_for_tcp_port`, `_cmdline_suggests_koru_serve*`, `_try_stop_prior_koru_serve_listener`), the bind retry loop (`_bind_fixed_port` / `_bind_auto_port`), and JSON I/O for `.planfile/.koru/serve-endpoint.json`. |
| [`koruapi/dashboard_routes.py`](../src/koruapi/dashboard_routes.py) | `build_dashboard_handler(config)` — the `BaseHTTPRequestHandler` subclass with one method per `GET`/`POST` route (`/api/dashboard`, `/api/context`, `/api/topology`, `/api/runtime-context`, `/api/handoff`, `/api/tickets/*`, …). HTML template is loaded once via `@lru_cache` and shared across requests. |
| [`koruapi/dashboard_template.html`](../src/koruapi/dashboard_template.html) | Single-file HTML/CSS/JS for the operator dashboard (auto-refresh, tabs, ticket forms, topology toggles, settings, link to `/grid`). Read at first `GET /`. |

All public names from the pre-refactor `dashboard_serve` module are still
re-exported from `koruapi.dashboard_serve` (and `koru.serve`, which is an
alias module), so callers like `koru.autonomy.operator_pipeline.py` and
`tests/test_serve.py` keep working unchanged.

Adding a new route is a single-file change in `dashboard_routes.py`:
add a method on the inner `_Handler` class and register the path in the
inline route dict inside `do_GET` (for read-only endpoints) or `do_POST`
(for mutations).

### Activity log

Set `KORU_ACTIVITY_LOG=1` (default) for timestamped lines:

```text
[12:00:01] koru ▸ API: invoke scan.apply method=run project=…
[12:00:02] koru ▸ CHAT: drive → ide=cursor …
```

### Integration ids (sample)

`context.build`, `doctor.run`, `scan.apply`, `queue.loop`, `gate.regix`,
`autopilot.status`, `autopilot.drive`, `planfile.tickets`,
`mcp.list_tickets`, `mcp.run_ticket`, `mcp.quality_gates`,
`dsl.to_library`, `dsl.to_dsl`, `dsl.roundtrip`, `topology.read`

Full list: `python -c "from koruapi import list_integrations; print([s.id for s in list_integrations()])"`
