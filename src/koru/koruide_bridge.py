"""Wire koru's real host implementations onto :mod:`koruide.host_hooks`.

``koruide`` is standalone-importable and only talks to the koru host
through the late-bound callables in ``koruide.host_hooks``.  This module
is the koru side of that seam: :func:`install_koruide_host_hooks` pins the
real koru functions onto the hook registry and must run before the
autopilot daemon serves its first message (see
``koru.autopilot.daemon_cli.run_daemon_command``).

Even without this explicit wiring the hook defaults lazily resolve the
same koru functions at call time, so behaviour under a koru host is
identical; installing them here merely makes the binding explicit and
import-order independent.
"""

from __future__ import annotations


def install_koruide_host_hooks() -> None:
    """Install koru's implementations for every koruide host hook."""
    from koru.control_commands import plugin_socket_command
    from koru.integration_ledger import record_integration_action
    from koru.observability_events import (
        emit_action,
        emit_decision,
        emit_failure,
        emit_intent,
        emit_phase,
        emit_verify,
    )
    from koruide import host_hooks

    host_hooks.set_host_hooks(
        record_integration_action=record_integration_action,
        plugin_socket_command=plugin_socket_command,
        emit_action=emit_action,
        emit_decision=emit_decision,
        emit_failure=emit_failure,
        emit_intent=emit_intent,
        emit_phase=emit_phase,
        emit_verify=emit_verify,
    )


__all__ = ["install_koruide_host_hooks"]
