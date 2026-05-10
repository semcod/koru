# testql — declarative testing scenarios (oqlos)

## Co to jest

Deklaratywny język testowy (YAML/TOON) dla scenariuszy API + UI.
**W większości LLM-free** — scenariusze są pisane manualnie lub
generowane przez Windsurf agenta. Format TOON jest 30-60% mniejszy od
JSON-a w kontekście LLM.

W c2004 testql-watchdog uruchamia 50 assertions co 60s jako active
probing.

## Kiedy używać

| Scenariusz | Komenda | LLM? |
|---|---|---|
| Active probing 50 endpointów (auto) | testql-watchdog cron | ❌ |
| Manualny probe ad-hoc | `task monitor:probe` | ❌ |
| Uruchomienie konkretnego scenariusza | `testql run <scenario>.testql.yaml` | ❌ |
| Generowanie nowego scenariusza | (manual lub via Windsurf) | LLM Windsurfa |
| MCP tool dla Windsurf | `python3 -m testql.mcp.server` | ❌ |

## Konfiguracja

### Scenariusze (gdzie pisać)

`@/home/tom/github/maskservice/c2004/testql-testing/scenarios/`:

```yaml
# realtime-health.testql.toon.yaml — przykład
name: c2004 realtime health
target: http://localhost:8101
scenarios:
  - name: backend health
    steps:
      - GET /api/v3/health
      - assert status == 200
      - assert json.status == "ok"
  - name: frontend reachability
    target: http://localhost:8100
    steps:
      - GET /
      - assert status == 200
```

### Env vars

```bash
TESTQL_PROJECT=/home/tom/github/maskservice/c2004
TESTQL_BASE_URL=http://localhost:8101
TESTQL_TIMEOUT=10
```

## Komendy

```bash
# Run pojedynczy scenariusz
testql run testql-testing/scenarios/realtime-health.testql.toon.yaml

# Run całego suite
testql suite all

# Watch mode (re-run on file changes)
testql watch

# Topology — wizualizacja zależności endpointów
testql topology

# MCP server
python3 -m testql.mcp.server
```

## Output

```
✓ backend health         200  3.2ms
✓ frontend reachability  200  12.8ms
✓ /api/v3/users          200  45.1ms (50 of 50 assertions OK)

50 passed in 8.3s
```

## Integracja z c2004

| Miejsce | Cel |
|---|---|
| `@/home/tom/github/maskservice/c2004/testql-testing/scenarios/` | Wszystkie scenariusze (~10 plików) |
| `@/home/tom/github/maskservice/c2004/monitoring/testql-watchdog/` | Container running scenarios co 60s |
| `@/home/tom/github/maskservice/c2004/Taskfile.yml` | `task monitor:probe` |
| `@/home/tom/github/maskservice/c2004/.windsurf/mcp_config.example.json` | MCP entry |
| `@/home/tom/github/maskservice/c2004/.windsurf/workflows/testql-autoloop.md` | Autonomous stabilization workflow |

## Format TOON vs JSON

TOON to compact format dla LLM context:

```toon
GET /api/v3/health → 200 status=ok
GET /api/v3/users → 200 count=12
```

vs JSON:

```json
{"method":"GET","path":"/api/v3/health","expect":{"status":200,"body":{"status":"ok"}}}
```

→ **30-60% taniej w tokenach**. W c2004 wszystkie scenariusze używają TOON.

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `testql: command not found` | `pip install --user testql` |
| Watchdog nie uruchamia | `docker logs c2004-testql-watchdog --tail 50` |
| Scenario fails ale endpoint OK | Sprawdź `TESTQL_BASE_URL` w docker-compose env |
| MCP server: warning frozen | Ignorowalne (`runpy` warning) |

## Linki

- Repo: https://github.com/oqlos/testql (lokalnie: `/home/tom/github/oqlos/testql`)
- Wersja: `0.2.0` (editable)
- W c2004: 10 scenariuszy, 50 assertions, runs co 60s
