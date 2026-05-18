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
