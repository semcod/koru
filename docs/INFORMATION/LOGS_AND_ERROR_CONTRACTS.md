---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "logs-and-error-contracts",
  "kind": "information",
  "version": 1,
  "title": "Structured logging, SODL event model and error contracts",
  "status": "implemented",
  "owner": "semcod/koru",
  "scope": "repository",
  "updated": "2026-09-27",
  "source_revision": "2c82e2055feb269399c3081ec6750e5b5ee9b7df",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/koru/commit/2c82e2055feb269399c3081ec6750e5b5ee9b7df",
    "https://github.com/semcod/koru/blob/main/src/koru/data/wellmanifest-logs-contract-v0.3.json"
  ]
}
---

# Structured logging, SODL event model and error contracts

<!-- docs:section summary -->
## Summary

Koru 0.1.461 implements structured logging and deterministic error contracts complying with Wellmanifest Logs standard v0.5.0, providing correlation tracking and standardized error classification across autonomous cycles.

<!-- docs:section details -->
## Details

Telemetry and error handling adhere to canonical schemas:

1. **Correlation tracking**: Every discrete operation carries an explicit correlation identifier. Subprocesses log with `corr=process-<uuid>`, while queue and tillm autopilot operations emit `corr=operator-<action>-<uuid>` for end-to-end traceability.
2. **SODL and OQL event format**: Operational logs output structured key-value payloads containing timestamp, log level, event kind, correlation ID, project target, and JSON-encoded event payload.
3. **Log contract enforcement**: Telemetry structures conform to `src/koru/data/wellmanifest-logs-contract-v0.3.json`. Governance verifies this contract via `.governance/standard-pack-evidence/logs.json`.
4. **Standard error taxonomy**:
   - `GOV-*`: Governance admission gates (e.g. `GOV-MATERIAL-001`, `GOV-TICKET-ALLOCATION-003`).
   - `AUTO-*`: Autopilot and autonomy runtime states (e.g. cycle skips, drive retries).
   - `LIM-*`: Physical/environmental limits governed by Wellmanifest NoLimits (`LIM-STORAGE-001` through `LIM-COST-010`).
   - `KORU-*`: CLI parser, pipeline, and tool integration errors.
5. **Hourly rotation and diagnostic persistence**: Operational logs rotate hourly into local diagnostic sinks under `.subactor/receipts/`, avoiding repository pollution.

<!-- docs:section validation -->
## Validation

Contract adherence is verified by:
- Standard pack checker: `python3 .governance/standard_pack_check.py` validates SHA-256 integrity of logs contract artifacts.
- Journal inspection: `journalctl --user -u koru-lane-koru | grep "corr="` validates formatting of live correlation logs.

<!-- docs:section risks -->
## Risks

- **Log volume bloat**: Rapid queue cycles can generate excessive diagnostic volume. Handled by hourly rotation and retention ceilings.
- **Contract drift**: Upgrading logs standard requires updating both JSON schema artifacts and governance digest locks.
- **Next steps**: Implement automated anomaly detection on `corr=` traces to flag recurring error cascades.
