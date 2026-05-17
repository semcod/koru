# KIDE-002 — Spec `API v1` (NDJSON)

- Status: Draft
- Date: 2026-05-16
- Related TODO: `KIDE-002`
- Source of truth (current impl): `src/koru/autopilot/protocol.py`, `src/koru/autopilot/daemon.py`

## 1. Zakres

Ten dokument formalizuje aktualny kontrakt wire protocol (`v1`) używany przez:

- CLI client ↔ daemon,
- plugin IDE ↔ daemon,
- daemon ↔ plugin IDE.

`API v1` jest line-based, bez jawnego pola `version`.

## 2. Transport

- Kanał: Unix domain socket (`AF_UNIX`, stream).
- Kodowanie: UTF-8.
- Ramka: jeden JSON na linię (NDJSON), linia kończy się `\n`.
- Limit rozmiaru: `MAX_LINE_BYTES = 1 MiB`.
- Polityka błędu: nieznane typy i błędne ramki zwracają `error`.

## 3. Envelope `v1`

### 3.1 Kształt

```json
{
  "type": "drive",
  "id": "cli-drive",
  "text": "continue",
  "submit": true,
  "ide": "auto"
}
```

### 3.2 Pola bazowe

- `type` (required, `string`) — typ wiadomości.
- `id` (optional, `string`) — correlation id.
- Pozostałe pola zależne od `type`.

### 3.3 Walidacja

- `type` musi należeć do zbioru `ALL_TYPES`.
- `id` (jeśli obecne) musi być stringiem.
- Dla typów z whitelistą pól, pola spoza schematu są odrzucane.
- Dla `ack`/`error` dozwolone są dowolne pola informacyjne (poza `type`, `id`).

## 4. Typy wiadomości (pełna lista)

### 4.1 Plugin -> daemon

- `hello`
- `session.started`
- `session.ended`
- `message.sent`
- `message.received`
- `status.error`
- `ack`
- `error`

### 4.2 Daemon -> plugin

- `chat.send`
- `ping`
- `shutdown`
- `ack`
- `error`

### 4.3 CLI -> daemon

- `drive`
- `status`
- `shutdown`
- `ping`

## 5. Schemat pól per typ

| Type | Dozwolone pola payload | Wymagania semantyczne |
| --- | --- | --- |
| `hello` | `ide`, `version`, `pid` | `ide` musi być niepustym stringiem |
| `session.started` | `chat` | brak dodatkowych wymagań |
| `session.ended` | `chat`, `reason` | brak dodatkowych wymagań |
| `message.sent` | `chat`, `text`, `length` | brak dodatkowych wymagań |
| `message.received` | `chat`, `text`, `summary` | brak dodatkowych wymagań |
| `status.error` | `message`, `severity`, `source` | brak dodatkowych wymagań |
| `chat.send` | `text`, `submit` | `text` oczekiwany przez plugin |
| `drive` | `text`, `submit`, `ide`, `require_plugin` | `text` musi być niepustym stringiem |
| `ping` | (brak) | brak |
| `shutdown` | (brak) | brak |
| `status` | (brak) | brak |
| `ack` | dowolne | zwykle `ok` + info |
| `error` | dowolne | zwykle `ok=false`, `message` |

## 6. Kody błędów (kanoniczne mapowanie v1)

Uwaga: `v1` nie ma osobnego pola `code` na wire. Dla spójności klienta definiujemy
kanoniczne kody mapowane z treści błędów.

| Code | Source | Typowy `message` |
| --- | --- | --- |
| `line_too_large` | decoder/daemon | `line too large` |
| `invalid_json` | decoder | `invalid json: ...` |
| `non_utf8` | decoder | `non-utf-8 line: ...` |
| `empty_line` | decoder | `empty line` |
| `missing_type` | decoder | `missing 'type' string field` |
| `unknown_type` | decoder | `unknown message type: ...` |
| `invalid_id` | decoder | `'id' must be a string when present` |
| `unhandled_type` | daemon dispatch | `unhandled type '...'` |
| `missing_text` | `drive` handler | `missing 'text'` |
| `missing_ide` | `hello` handler | `hello requires 'ide'` |
| `plugin_required_unavailable` | `drive` handler | `no connected autopilot plugin for ide=...` |
| `backend_injector_error` | injection path | treść wyjątku `InjectorError` |

## 7. Przykłady request/response (per typ)

### 7.1 `hello`

Request:
```json
{"type":"hello","id":"h1","ide":"vscode","version":"0.1.0","pid":1234}
```
Response:
```json
{"type":"ack","id":"h1","ok":true,"role":"plugin"}
```

### 7.2 `drive`

Request:
```json
{"type":"drive","id":"cli-drive","text":"continue with the next ticket","submit":true,"ide":"auto","require_plugin":false}
```
Response (success):
```json
{"type":"ack","id":"cli-drive","ok":true,"backend":"plugin","submitted":true}
```
Response (error):
```json
{"type":"error","id":"cli-drive","ok":false,"message":"missing 'text'"}
```

### 7.3 `status`

Request:
```json
{"type":"status","id":"cli-status"}
```
Response:
```json
{"type":"ack","id":"cli-status","ok":true,"socket":"/run/user/1000/koru-autopilot.sock","plugins":[],"backends":[],"selected_backend":null,"ides":[]}
```

### 7.4 `ping`

Request:
```json
{"type":"ping","id":"health"}
```
Response:
```json
{"type":"ack","id":"health","ok":true,"pong":true}
```

### 7.5 `shutdown`

Request:
```json
{"type":"shutdown","id":"cli-shutdown"}
```
Response:
```json
{"type":"ack","id":"cli-shutdown","ok":true,"stopping":true}
```

### 7.6 `chat.send` (daemon -> plugin)

Command:
```json
{"type":"chat.send","id":"r1","text":"next ticket please","submit":true}
```
Plugin ack:
```json
{"type":"ack","id":"r1","ok":true,"delivered":true,"submitted":true}
```

### 7.7 `session.started`

Event:
```json
{"type":"session.started","id":"ev1","chat":"cascade"}
```
Ack:
```json
{"type":"ack","id":"ev1","ok":true,"event":"session.started"}
```

### 7.8 `session.ended`

Event:
```json
{"type":"session.ended","id":"ev2","chat":"cascade","reason":"user-stop"}
```
Ack (example):
```json
{"type":"ack","id":"ev2","ok":true,"event":"session.ended","handoff":"sent","chars":412}
```

### 7.9 `message.sent`

Event:
```json
{"type":"message.sent","id":"m1","chat":"cascade","text":"run tests","length":9}
```
Ack:
```json
{"type":"ack","id":"m1","ok":true,"event":"message.sent"}
```

### 7.10 `message.received`

Event:
```json
{"type":"message.received","id":"m2","chat":"cascade","summary":"tests green"}
```
Ack:
```json
{"type":"ack","id":"m2","ok":true,"event":"message.received"}
```

### 7.11 `status.error`

Event:
```json
{"type":"status.error","id":"se1","message":"chat input not focused","severity":"warning","source":"plugin"}
```
Ack:
```json
{"type":"ack","id":"se1","ok":true,"event":"status.error"}
```

### 7.12 `ack`

Plugin response to `chat.send`:
```json
{"type":"ack","id":"drive-123","ok":true,"delivered":true}
```
Daemon relays ack to waiting CLI with tym samym `id`.

### 7.13 `error`

Generic error envelope:
```json
{"type":"error","id":"req-1","ok":false,"message":"unknown message type: 'foo'"}
```

## 8. Kompatybilność

- `API v1` jest wymagane i utrzymywane podczas migracji do `v2`.
- Nowe implementacje (`koruide`) MUSZĄ obsługiwać `v1` do czasu zakończenia rollout (`KIDE-022..024`).

## 9. Kryteria akceptacji (`KIDE-002`)

- Pełna lista typów wiadomości jest opisana.
- Pola per typ i wymagania semantyczne są jawne.
- Kanoniczne mapowanie kodów błędów jest zdefiniowane.
- Istnieje przykład request/response dla każdego typu z `ALL_TYPES`.
