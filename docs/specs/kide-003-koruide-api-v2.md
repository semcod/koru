# KIDE-003 — Spec `API v2` (envelope + compatibility)

- Status: Draft
- Date: 2026-05-16
- Related TODO: `KIDE-003`, `KIDE-004`
- Depends on: `docs/specs/kide-002-koruide-api-v1.md`

## 1. Cel

`API v2` wprowadza jawny envelope i wersjonowanie kontraktu, przy zachowaniu
kompatybilności z `v1` podczas migracji.

Cele:

- stabilna warstwa między `koru` a `koruide`,
- jednoznaczne błędy (`code`, `message`, `retryable`),
- capability negotiation,
- przewidywalny fallback do `v1`.

## 2. Envelope `v2`

### 2.1 Kształt bazowy

```json
{
  "version": "2.0",
  "type": "command.drive",
  "id": "req-123",
  "ts": "2026-05-16T14:51:00Z",
  "source": {"role": "koru", "id": "cli"},
  "target": {"role": "daemon", "id": "local"},
  "payload": {
    "text": "continue with the next ticket",
    "submit": true,
    "ide": "auto"
  }
}
```

### 2.2 Pola

- `version` (required, `string`) — np. `2.0`.
- `type` (required, `string`) — typ domenowy (`command.*`, `event.*`, `response.*`).
- `id` (required, `string`) — correlation id, unikalny per request.
- `ts` (required, RFC3339 UTC) — timestamp nadawcy.
- `source` (required, object) — `{role,id}`.
- `target` (optional, object) — `{role,id}`.
- `payload` (optional, object) — dane operacji.
- `error` (optional, object) — obecne dla odpowiedzi negatywnych.

### 2.3 Obiekt `error`

```json
{
  "code": "missing_text",
  "message": "missing 'text'",
  "retryable": false,
  "details": {"field": "text"}
}
```

## 3. Typy operacji `v2`

### 3.1 Komendy

- `command.hello`
- `command.drive`
- `command.status`
- `command.ping`
- `command.shutdown`
- `command.chat.send`

### 3.2 Eventy

- `event.session.started`
- `event.session.ended`
- `event.message.sent`
- `event.message.received`
- `event.status.error`

### 3.3 Odpowiedzi

- `response.ok`
- `response.error`

## 4. Capability negotiation (`KIDE-004` alignment)

### 4.1 Handshake

1. Client/plugin wysyła `command.hello` z:
   - `payload.api_versions_supported` (np. `["1.0", "2.0"]`),
   - `payload.capabilities`.
2. Server odpowiada `response.ok` z:
   - `payload.api_version_selected`,
   - `payload.capabilities_effective`.

### 4.2 Przykład

Request:
```json
{
  "version":"2.0",
  "type":"command.hello",
  "id":"h-1",
  "ts":"2026-05-16T14:51:00Z",
  "source":{"role":"plugin","id":"vscode"},
  "payload":{
    "api_versions_supported":["1.0","2.0"],
    "capabilities":["chat.send","session.events"]
  }
}
```

Response:
```json
{
  "version":"2.0",
  "type":"response.ok",
  "id":"h-1",
  "ts":"2026-05-16T14:51:00Z",
  "source":{"role":"daemon","id":"local"},
  "payload":{
    "api_version_selected":"2.0",
    "capabilities_effective":["chat.send","session.events"]
  }
}
```

## 5. Mapowanie `v1 -> v2`

| `v1` type | `v2` type | Mapowanie payload |
| --- | --- | --- |
| `hello` | `command.hello` | `ide/version/pid` -> `payload.*` |
| `drive` | `command.drive` | `text/submit/ide/require_plugin` -> `payload.*` |
| `status` | `command.status` | brak payload |
| `ping` | `command.ping` | brak payload |
| `shutdown` | `command.shutdown` | brak payload |
| `chat.send` | `command.chat.send` | `text/submit` -> `payload.*` |
| `session.started` | `event.session.started` | `chat` -> `payload.chat` |
| `session.ended` | `event.session.ended` | `chat/reason` -> `payload.*` |
| `message.sent` | `event.message.sent` | `chat/text/length` -> `payload.*` |
| `message.received` | `event.message.received` | `chat/text/summary` -> `payload.*` |
| `status.error` | `event.status.error` | `message/severity/source` -> `payload.*` |
| `ack` | `response.ok` | `ok=true` + reszta -> `payload` |
| `error` | `response.error` | `message` + mapped `code` -> `error.*` |

## 6. Macierz kompatybilności (`v1 <-> v2`)

| Client | Server | Wynik |
| --- | --- | --- |
| `v1-only` | `v1+v2` | działa na `v1` |
| `v2-only` | `v1-only` | fallback do `v1` przez adapter/proxy lub błąd `unsupported_version` |
| `v2-prefers, v1-fallback` | `v1+v2` | negocjuje `v2`, fallback do `v1` jeśli brak capability |
| `v1+v2` | `v2-only` | negocjuje `v2` |

## 7. Reguły migracji i fallback

1. Priorytet: próbuj `v2`, fallback do `v1` jeśli:
   - timeout handshake,
   - `unsupported_version`,
   - brak wymaganej capability.
2. Fallback nie może zmieniać semantyki operacji (`drive`, `status`, `shutdown`).
3. Przy fallback loguj zdarzenie z kodem:
   - `fallback_v2_to_v1`.
4. `v1` utrzymujemy do zamknięcia canary rollout (`KIDE-022..024`).

## 8. Kody błędów `v2`

Minimalny zestaw:

- `unsupported_version`
- `unsupported_type`
- `invalid_payload`
- `missing_text`
- `missing_ide`
- `plugin_required_unavailable`
- `backend_unavailable`
- `backend_execution_failed`
- `timeout`
- `internal_error`

## 9. Idempotencja i timeout

- `id` jest idempotency key dla komend typu write (`command.chat.send`, `command.drive`).
- Server powinien ignorować duplikaty `id` w krótkim oknie deduplikacji.
- Timeout referencyjny:
  - handshake: 2s,
  - `status`/`ping`: 2s,
  - `drive`/`chat.send`: 10s.

## 10. Przykłady odpowiedzi

### 10.1 `response.ok`

```json
{
  "version":"2.0",
  "type":"response.ok",
  "id":"req-123",
  "ts":"2026-05-16T14:51:10Z",
  "source":{"role":"daemon","id":"local"},
  "payload":{"backend":"plugin","submitted":true}
}
```

### 10.2 `response.error`

```json
{
  "version":"2.0",
  "type":"response.error",
  "id":"req-123",
  "ts":"2026-05-16T14:51:10Z",
  "source":{"role":"daemon","id":"local"},
  "error":{
    "code":"missing_text",
    "message":"missing 'text'",
    "retryable":false,
    "details":{"field":"text"}
  }
}
```

## 11. Kryteria akceptacji (`KIDE-003`)

- Zdefiniowany envelope `v2` z polami `version/type/id/payload/error`.
- Opisana macierz kompatybilności `v1<->v2`.
- Jawne reguły migracji i fallback przy nieobsługiwanej wersji/capability.
- Zdefiniowany minimalny katalog kodów błędów `v2`.
