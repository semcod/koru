"""One-command observation mesh orchestrator.

``koruobserve`` glues together :mod:`koru.configurator`, :mod:`korumesh`,
:mod:`koruvision`, and :mod:`koruapi` so users can launch the full screenshot
mesh + dashboard with a single command. It does not implement any capture,
transport, or dashboard logic itself — it just bootstraps config, manages PIDs
of background processes, and prints the URL of the grid view.
"""

from koruobserve.lifecycle import ObserveProcesses, observe_down, observe_status, observe_up

__all__ = ["ObserveProcesses", "observe_down", "observe_status", "observe_up"]
