# Prompt: warstwa kontroli `*2{pkg}`

> Szablon do wklejenia w Cursor/LLM. Zamień `{pkg}` na nazwę paczki (np. `doql`, `testql`, `oql`).
> Przykład: `{pkg}` → `doql` daje `mcp2doql`, `dsl2doql`, …

---

## Prompt (kopiuj od linii poniżej)

```
Zrefaktoryzuj / utwórz warstwę kontroli dla paczki `{pkg}` w monorepo.

## Cel

Paczka `{pkg}` ma być sterowana wyłącznie przez standaryzowany DSL i bus CQRS/ES.
Adaptery wejścia (MCP, REST, CLI, URI, NL) nie zawierają logiki domenowej — tylko delegują do `dsl2{pkg}`.

## Wymagane paczki w `packages/`

| Paczka | Rola | Dozwolone zależności |
|--------|------|----------------------|
| `dsl2{pkg}` | Grammar DSL + **JSON Schema** + **Protobuf** + CQRS bus + EventStore | `{pkg}` (core), `protobuf`, stdlib |
| `uri2{pkg}` | `uri://` → linia DSL → `dsl2{pkg}.dispatch()` | `dsl2{pkg}` |
| `nlp2{pkg}` | NL → linia DSL (bez side-effect) → opcjonalnie `dispatch()` | `dsl2{pkg}` |
| `cli2{pkg}` | Shell REPL / exec / run script | `dsl2{pkg}` |
| `mcp2{pkg}` | Serwer MCP (stdio), narzędzia = cienkie wrappery DSL | `dsl2{pkg}` |
| `rest2{pkg}` | REST API (FastAPI), endpointy = cienkie wrappery DSL | `dsl2{pkg}` |

Reguły twarde:
- JEDYNY punkt wykonania mutacji: `dsl2{pkg}.dispatch()` → `CommandHandler`
- Query (read-only): `QueryHandler` — bez zapisu eventów
- Command (write): append event do EventStore, potem handler
- Adaptery NIE importują się nawzajem (wyjątek: wszystkie → `dsl2{pkg}`)
- Logika domenowa (parse, validate, export, adopt, konwertery) zostaje w `{pkg}/`, nie w adapterach
- Ta sama linia DSL daje identyczny wynik z CLI, URI, MCP, REST

## Schemat przepływu (docelowy)

```mermaid
flowchart TB
  subgraph adapters [Adaptery wejścia — packages]
    NL[nlp2{pkg}]
    URI[uri2{pkg}]
    CLI[cli2{pkg}]
    MCP[mcp2{pkg}]
    REST[rest2{pkg}]
  end

  subgraph control [Warstwa kontroli]
    TXT[linia tekstowa DSL]
    SCH[JSON Schema\nvalidate]
    PB[Protobuf\nCommand/Query/Event]
    DSL[dsl2{pkg}.dispatch]
    Q[QueryHandler]
    C[CommandHandler]
    ES[(EventStore\n*.events.pb / *.jsonl)]
  end

  subgraph domain [Domena — {pkg}/]
    P[parse / validate]
    A[adopt / import]
    X[export / materialize]
  end

  NL -->|"NL → linia DSL"| TXT
  URI -->|"uri → linia DSL"| TXT
  CLI -->|"linia DSL"| TXT
  MCP -->|"linia DSL / pb"| TXT
  REST -->|"linia DSL / pb"| TXT

  TXT --> SCH
  SCH --> PB
  PB --> DSL

  DSL -->|QUERY RESOLVE VALIDATE| Q
  DSL -->|PATCH APPEND GENERATE ADOPT …| C
  C --> ES
  Q --> P
  C --> P
  Q --> X
  C --> X
  C --> A
```

## Schemat URI (dwa poziomy)

1. **Adres zasobu** (target komendy):
   `{pkg}://block/entity/Contact?file=app.{pkg}.less`

2. **Adres komendy DSL** (opcjonalnie, uri2{pkg}):
   `{pkg}://cmd/QUERY?target={pkg}://block/app&file=app.{pkg}.less&format=less`

`uri2{pkg}` dekoduje URI → **jedna linia DSL** → `dsl2{pkg}.dispatch()`.

## DSL: tekst + Schema + Protobuf

Warstwa `dsl2{pkg}` utrzymuje **trzy reprezentacje** tej samej komendy:

| Reprezentacja | Pliki | Rola |
|---------------|-------|------|
| **Tekst** (canonical UX) | `*.dsl`, REPL, CLI | czytelna linia: `QUERY …` |
| **JSON Schema** | `schema/commands/*.schema.json` | walidacja pól, dokumentacja, codegen |
| **Protobuf** | `proto/dsl2{pkg}/v1/*.proto` | serializacja REST/MCP/ES, wersjonowanie |

### Przepływ kodowania

```text
linia tekstowa DSL
  → parse (grammar.py) → dict (JSON-like)
  → validate (jsonschema) → Command | Query message
  → SerializeToString (protobuf) → bus.dispatch(pb)
  → handler → Result (protobuf)
  → opcjonalnie: to_text() / to_json() dla CLI
```

Reguły:
- **Schema jest źródłem prawdy** dla pól komend (nazwy, typy, required).
- **Protobuf odzwierciedla Schema** — każdy `verb` ma message `XxxCommand` / `XxxQuery`.
- Tekst DSL to **składnia cukrowa** nad Schema (nie odwrotnie).
- EventStore preferuje **protobuf** (`*.events.pb` lub base64 w jsonl); jsonl dozwolony w dev.
- REST/MCP akceptują: `text/plain` (linia DSL), `application/json` (dict), `application/x-protobuf`.

### Przykład Schema (`schema/commands/query.schema.json`)

```json
{
  "$id": "dsl2{pkg}/commands/query",
  "type": "object",
  "required": ["verb", "target"],
  "properties": {
    "verb": { "const": "QUERY" },
    "target": { "type": "string", "format": "uri", "pattern": "^{pkg}://" },
    "file": { "type": "string" },
    "format": { "enum": ["json", "yaml", "less"], "default": "json" }
  },
  "additionalProperties": false
}
```

### Przykład Protobuf (`proto/dsl2{pkg}/v1/command.proto`)

```protobuf
syntax = "proto3";
package dsl2{pkg}.v1;

message QueryCommand {
  string target = 1;   // {pkg}://block/...
  string file = 2;
  string format = 3;   // json|yaml|less
}

message PatchCommand {
  string target = 1;
  string file = 2;
  string with_path = 3;
  bytes with_content = 4;  // opcjonalnie inline zamiast pliku
}

message DslEnvelope {
  string verb = 1;     // QUERY | PATCH | VALIDATE | ...
  oneof body {
    QueryCommand query = 10;
    PatchCommand patch = 11;
    // … pozostałe komendy
  }
  string default_file = 20;
  string correlation_id = 21;
}

message DslResult {
  bool ok = 1;
  string verb = 2;
  string output = 3;
  bytes data_json = 4;   // structured payload
  string error = 5;
  string event_id = 6;   // Commands only
}

message DslEvent {
  string id = 1;
  int64 ts_unix = 2;
  DslEnvelope command = 3;
  DslResult result = 4;
}
```

### Generacja kodu (oczekiwana)

```bash
# w packages/dsl2{pkg}/
buf generate                    # lub: protoc → src/dsl2{pkg}/gen/
python -m dsl2{pkg}.codegen     # schema → typed dataclasses / pydantic (opcjonalnie)
```

Wygenerowane moduły:
- `src/dsl2{pkg}/gen/` — `*_pb2.py` z `.proto`
- `src/dsl2{pkg}/schema/` — kopie `.schema.json` + `registry.py` (verb → schema)

## Grammar DSL tekstowa (minimum)

Jedna linia = jedna komenda. Komentarz: `#`.

| Typ | Komendy |
|-----|---------|
| Query | `QUERY`, `RESOLVE`, `VALIDATE` |
| Command | `PATCH`, `APPEND`, `MATERIALIZE`, `GENERATE`, `ADOPT`, `CONVERT` |

Przykłady:
```text
QUERY {pkg}://block/app?file=app.{pkg}.less FORMAT json
VALIDATE app.{pkg}.less
PATCH {pkg}://block/entity/Contact?file=app.{pkg}.less WITH contact.patch.less
APPEND app.{pkg}.less WITH workflow.fragment.less
GENERATE "CRM z kontaktami" OUT app.{pkg}.less
ADOPT . OUT app.{pkg}.less
CONVERT scenarios/test.oql OUT workflow.less
RESOLVE "pokaż workflow install" FILE app.{pkg}.less
```

## CQRS / EventStore

- `QueryResult` / `CommandResult`: protobuf `DslResult` (+ opcjonalny JSON export)
- `Event`: protobuf `DslEvent` (command + result + metadata)
- Store: `{pkg}.events.pb` (preferowany) lub `{pkg}.events.jsonl` (dev fallback, base64 pb)
- Replay: `dsl2{pkg} replay --file app.{pkg}.less` (odczyt sekwencji `DslEvent`)
- Walidacja przed dispatch: **schema JSON** → **parse protobuf** → handler

## Kontrakty adapterów

### cli2{pkg}
```bash
cli2{pkg} shell [--file app.{pkg}.less]
cli2{pkg} exec 'QUERY {pkg}://block/app'
cli2{pkg} run script.dsl
dsl2{pkg} validate-schema
dsl2{pkg} encode 'QUERY {pkg}://block/app' --format protobuf
dsl2{pkg} decode --input command.pb --format protobuf
```

### uri2{pkg}
```bash
uri2{pkg} decode --uri '{pkg}://cmd/QUERY?...'     # → linia DSL
uri2{pkg} run --uri '{pkg}://cmd/PATCH?...'       # decode + dispatch
uri2{pkg} resolve "pokaż app" --file app.{pkg}.less  # NL hints → URI komendy
```

### nlp2{pkg}
```bash
nlp2{pkg} to-dsl "validate app.{pkg}.less"          # tylko DSL, bez wykonania
nlp2{pkg} apply "validate app.{pkg}.less"           # to-dsl + dispatch
nlp2{pkg} generate "CRM" --out app.{pkg}.less       # istniejąca generacja (Command)
```

### mcp2{pkg}
```bash
mcp2{pkg} serve
```
Narzędzia MCP (minimum):
- `{pkg}_run_dsl(script: str, default_file: str = "")`
- `{pkg}_run_command(command: str, default_file: str = "")`
- `{pkg}_run_command_pb(envelope_bytes: bytes) -> bytes`  # protobuf
- `{pkg}_to_dsl(prompt: str) -> str`

### rest2{pkg}
```bash
rest2{pkg} serve --port 8xxx
```
Endpointy (minimum):
- `POST /v1/dsl` — `Content-Type: text/plain` (linia) lub `application/json` (dict) lub `application/x-protobuf` (`DslEnvelope`)
- `POST /v1/commands` — alias; body zgodny ze Schema
- `GET /v1/schema/{verb}` — JSON Schema komendy
- `GET /v1/proto` — descriptor / link do `.proto`
- `GET /v1/events?file=app.{pkg}.less` — stream `DslEvent` (pb lub json)
- `GET /health`

## Co przenieść do `{pkg}/` (core)

Jeśli logika jest w adapterze, przenieś do core:
- skanery adopt → `{pkg}/adopt/scanner/`
- konwertery formatów → `{pkg}/importers/`
- parse/validate/export → już w `{pkg}/`

Adapter zostaje cienkim mostem.

## Struktura katalogów (oczekiwana)

```
packages/
  dsl2{pkg}/
    proto/dsl2{pkg}/v1/
      command.proto       # DslEnvelope, *Command, *Query
      result.proto        # DslResult, DslEvent
    schema/commands/
      query.schema.json
      patch.schema.json
      validate.schema.json
      …                   # jeden plik schema na verb
    src/dsl2{pkg}/
      gen/                # wygenerowane *_pb2.py (buf/protoc)
      grammar.py          # tekst DSL → dict
      codec.py            # dict ↔ protobuf; validate(schema)
      schema_registry.py  # verb → JSON Schema
      bus.py              # dispatch(DslEnvelope | str | bytes)
      events.py           # EventStore (protobuf append)
      handlers/           # query_*.py, cmd_*.py
      cli.py              # exec / run / validate-schema / encode / decode
    buf.yaml              # opcjonalnie: buf generate
    pyproject.toml        # deps: protobuf, jsonschema, (buf build plugin)
  uri2{pkg}/src/uri2{pkg}/
    uri.py          # build/parse URI
    decode.py       # URI → linia DSL
    cli.py
  nlp2{pkg}/src/nlp2{pkg}/
    to_dsl.py       # NL → DSL
    apply.py        # to_dsl + dispatch
    cli.py
  cli2{pkg}/src/cli2{pkg}/
    shell.py
    cli.py
  mcp2{pkg}/src/mcp2{pkg}/
    server.py
    cli.py
  rest2{pkg}/src/rest2{pkg}/
    app.py          # FastAPI
    cli.py
```

## Kryteria akceptacji (must pass)

1. **Parity**: ta sama komenda (tekst / JSON / protobuf) → ten sam `DslResult` z:
   - `cli2{pkg} exec`
   - `uri2{pkg} run`
   - `mcp2{pkg}` tool `{pkg}_run_command`
   - `rest2{pkg}` POST `/v1/dsl`

2. **Schema**: każdy `verb` ma JSON Schema; `dsl2{pkg} validate-schema` przechodzi bez błędów.

3. **Protobuf**: `dsl2{pkg} encode/decode` round-trip: tekst → pb → tekst (semantycznie równoważne).

4. **Separacja**: `nlp2{pkg} to-dsl` nie mutuje plików; mutacja tylko przez `dispatch()`.

5. **CQRS**: Query nie zapisują eventów; Command appenduje `DslEvent` (protobuf).

6. **Brak cykli**: adaptery nie importują `{pkg}/cli` ani siebie nawzajem.

7. **Testy**:
   ```bash
   pytest packages/dsl2{pkg}/tests packages/uri2{pkg}/tests \
          packages/nlp2{pkg}/tests packages/cli2{pkg}/tests \
          packages/mcp2{pkg}/tests packages/rest2{pkg}/tests -q
   ```
   + test integracyjny parity (1 scenariusz × 4 adaptery × 3 formaty: text/json/pb).

8. **Dokumentacja**: każdy pakiet ma README z rolą, przykładami CLI, linkiem do `packages/README.md` i głównego README.

9. **Manifest** (jeśli dotyczy): wpisy w `app.{pkg}.less`:
   - `interface[type="cli"] page[name="cli2{pkg}"]`
   - `interface[type="mcp"] page[name="mcp2{pkg}"]`
   - `interface[type="api"] page[name="rest2{pkg}"]`

## Fazy implementacji

| Faza | Zakres |
|------|--------|
| 0 | `proto/` + `schema/` + codegen + `codec.py` (validate + encode/decode) |
| 1 | `dsl2{pkg}` bus + handlers + przepięcie `cli2{pkg}` |
| 2 | `uri2{pkg}` decode→DSL; `nlp2{pkg}` to-dsl; usunąć direct calls |
| 3 | `mcp2{pkg}` + `rest2{pkg}` (text + json + protobuf) |
| 4 | EventStore protobuf + replay + audit |

## Nie rób

- Nie duplikuj logiki domenowej w adapterach.
- Nie wołaj handlerów z `nlp2{pkg}` / `uri2{pkg}` omijając Schema + protobuf bus.
- Nie pomijaj `rest2{pkg}` — brak = fail kryteriów.
- Nie rozjedzaj Schema i Protobuf — zmiana verb wymaga obu + testu round-trip.
- Nie commituj bez uruchomienia testów.

Na końcu podaj: listę plików, diagram przepływu po refaktorze, wynik testów, znane luki Fazy 4.
```

---

## Przykład wypełniony: `{pkg}` = `doql`

Zamień w prompcie:
- `{pkg}` → `doql`
- manifest → `app.doql.less`
- EventStore → `app.doql.events.pb` (+ opcjonalny `.jsonl` w dev)
- Schema → `packages/dsl2doql/schema/commands/*.schema.json`
- Proto → `packages/dsl2doql/proto/dsl2doql/v1/*.proto`
- REST port → `8210` (przykład)

Oczekiwane paczki:
`dsl2doql`, `uri2doql`, `nlp2doql`, `cli2doql`, `mcp2doql`, `rest2doql`
