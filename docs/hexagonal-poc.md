# Hexagonal PoC — IDE control plane (koru-arch-1)

Status: **Phase 1 / port abstractions in place** — strangler-fig migration starts here.

## Why

The architecture audit (see chat transcript "PLF-1585 / koru-arch") identified
that:

- `src/koru/` has fan-out 537 — every refactor risks regressions in 3 unrelated places
- god modules (`autonomous_cycle.py` 2148L, `doctor.py` 1965L, `context.py` 1269L)
- `bounded_contexts/` already exists but is a thin event-logger over the legacy `autonomous_*.py` code path
- `extension.ts` (1582L) is a god class on the plugin side too

CQRS alone does not address the coupling problem. Hexagonal (Ports & Adapters)
does — and we already have the natural seam: the **NDJSON socket protocol**
between the VSCode/Cursor plugin and the Python daemon.

```
┌──────────────────────────────────┐
│ Adapter (TS): plugins/koru-      │
│ autopilot-vscode/extension.ts    │ ← target: thin (~300L)
└────────────┬─────────────────────┘
             │ NDJSON socket (already exists!)
┌────────────▼─────────────────────┐
│ Adapter (Py): koruide/client.py  │  KoruIDEClient
│                  + daemon/...    │
└────────────┬─────────────────────┘
             │ Ports  ← THIS PoC
┌────────────▼─────────────────────┐
│ Application: koru.autonomous_*,  │
│ koru.bounded_contexts.*          │
└────────────┬─────────────────────┘
             │
┌────────────▼─────────────────────┐
│ Domain: events, sagas, policies  │
└──────────────────────────────────┘
```

## Ports introduced (Phase 1)

`src/koruide/ports.py`:

- `IdeChatPort` — outbound: paste text + submit (drive)
- `IdeChatHistoryPort` — inbound: observe `message.received` from IDE-side LLM
- `IdeLifecyclePort` — health/shutdown of the daemon

All three are PEP 544 `Protocol`s (structural typing) with `@runtime_checkable`
so existing concrete classes satisfy them without modification.

Verified by `tests/test_koruide_ports.py`:

- `KoruIDEClient` already implements `IdeChatPort` and `IdeLifecyclePort`
  (no code change required to adopt)
- A trivial in-memory `_FakeChatAdapter` also satisfies `IdeChatPort` —
  application tests no longer need a Unix socket

## Strangler plan (Phase 2+)

Each ticket that touches `koru.autonomous_*` migrates a single call site:

```diff
- from koruide.client import KoruIDEClient
- def autopilot_step(text: str) -> bool:
-     client = KoruIDEClient()
-     return client.drive(text, submit=True).get("ok", False)

+ from koruide.ports import IdeChatPort, DriveOutcome
+ def autopilot_step(ide: IdeChatPort, text: str) -> DriveOutcome:
+     return ide.drive(text, submit=True)
```

In production wire `KoruIDEClient`. In tests inject a fake. Over 10–20 tickets,
the call sites stop importing concrete classes; god modules shrink because
the `IdeChat*Port` parameter is the obvious split point.

## What this PoC does NOT do (yet)

- does not migrate any existing call site (zero churn) — by design
- does not add dependency injection container — `IdeChatPort` is a function
  parameter, no framework needed
- does not split `extension.ts` — that is `koru-arch-2`
- does not introduce Saga state machine — that is `koru-arch-3`
- does not type events with Pydantic — that is `koru-arch-4`

## Next step

Pick a small caller in `koru.autonomous_*` (e.g. one helper that currently
does `KoruIDEClient().drive(...)`) and refactor it to take `ide: IdeChatPort`.
That is the first real strangler step — and it will already be testable
without spinning up the daemon.
