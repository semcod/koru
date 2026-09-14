# Ticket Changelog

## [0.1.0] - 2026-09-01

- Allocate the application workstream for leased issue execution and Living
  Status/SLA triage.
- Default autonomous claims to two hours and project a single Living Status
  through Planfile rather than a tracker-specific client.
- Escalate expired work to blocked human triage and expose lease expiry in
  `koru watch` output.

## [0.2.0] - 2026-09-14

- Set the default claim lease to one hour with a ten-minute takeover grace
  period.
- Emit one deduplicated, non-runnable Planfile handoff notice after the grace
  period; authoritative generation/fencing evidence remains required for a
  replacement agent to write.
