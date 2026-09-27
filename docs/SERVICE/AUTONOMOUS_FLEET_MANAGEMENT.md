---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "autonomous-fleet-management",
  "kind": "service",
  "version": 1,
  "title": "Autonomous fleet and service lifecycle management",
  "status": "implemented",
  "owner": "semcod/koru",
  "scope": "repository",
  "updated": "2026-09-27",
  "source_revision": "2c82e2055feb269399c3081ec6750e5b5ee9b7df",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/koru/commit/2c82e2055feb269399c3081ec6750e5b5ee9b7df",
    "https://github.com/semcod/koru/blob/main/src/koru/cli_fleet.py"
  ]
}
---

# Autonomous fleet and service lifecycle management

<!-- docs:section summary -->
## Summary

Koru 0.1.461 manages multi-repository autonomous lanes through supervisor-coordinated child processes and systemd user services. Autonomous daemons run headlessly without manual IDE intervention, ensuring continuous queue execution across projects.

<!-- docs:section details -->
## Details

Each managed repository executes an isolated autonomous lane via `koru autonomous up` or `koru fleet up`:

1. **Service lifecycle and systemd integration**: Project lanes operate as systemd user units (`koru-lane-<project>.service`). Units define restart policies, environment bindings, and drop-in overrides (`80-headless.conf`).
2. **Socket isolation**: To prevent cross-project interference, each lane listens on an isolated Unix domain socket (`/run/user/1000/koru-autopilot-<actor>.sock`) rather than sharing a global IDE port.
3. **Headless tillm driver**: Autopilot sessions drive LLM CLI backends (`claude-code`, `opencode`) non-interactively using `--agent-lane none` and `--replace-existing` to prevent stale zombie processes.
4. **Wayland headless compatibility**: Headless environments bind dummy display surfaces where IDE windowing hooks are required, allowing UI-bound automation without physical desktop sessions.

<!-- docs:section validation -->
## Validation

Fleet health is verified through the following checks:
- Service state: `systemctl --user status koru-lane-*` confirms active/running status across all lanes.
- Socket binding: `ls -la /run/user/1000/koru-autopilot-*.sock` verifies socket ownership and active listeners.
- Autonomy cycle verification: Inspection of journalctl logs confirms cycle increments and `pytest -p no:wellmanifest_governance` post-run executions.

<!-- docs:section risks -->
## Risks

- **Process collision**: Spawning unmanaged parallel daemons can lock repository planfiles. Mitigated by `--replace-existing` and lockfile heartbeats.
- **Resource exhaustion**: Running all lanes simultaneously requires CPU and memory throttling via systemd cgroups.
- **Next steps**: Expand automatic recovery handlers in `koru fleet` to detect stalled subprocesses without manual restarts.
