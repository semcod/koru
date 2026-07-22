"""Late-bound host-integration hooks for the koruide control plane.

``koruide`` can run standalone (without the ``koru`` distribution
installed).  Everything that reaches back into the koru host — the
integration ledger, observability event emitters and control-command
mirroring — is routed through the module-level callables below instead of
importing ``koru.*`` at module import time.

Resolution order for each hook:

1. Whatever the host explicitly installed via :func:`set_host_hooks`
   (koru does this from ``koru.koruide_bridge.install_koruide_host_hooks``
   before the autopilot daemon starts serving).
2. Otherwise the default lazily imports the real ``koru`` implementation
   at call time, so behaviour under a koru host is identical even when the
   bridge was not (yet) installed.
3. If ``koru`` is not importable at all (standalone koruide host) the
   default degrades to a silent no-op returning ``None``.

Callers must access the hooks late-bound (``host_hooks.emit_action(...)``
or through a thin module-local wrapper), never ``from koruide.host_hooks
import emit_action`` at module level, so host wiring takes effect.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

# hook name -> (koru module, attribute) providing the real implementation.
_HOOK_SPECS: dict[str, tuple[str, str]] = {
    "record_integration_action": ("koru.integration_ledger", "record_integration_action"),
    "plugin_socket_command": ("koru.control_commands", "plugin_socket_command"),
    "emit_action": ("koru.observability_events", "emit_action"),
    "emit_decision": ("koru.observability_events", "emit_decision"),
    "emit_failure": ("koru.observability_events", "emit_failure"),
    "emit_intent": ("koru.observability_events", "emit_intent"),
    "emit_phase": ("koru.observability_events", "emit_phase"),
    "emit_verify": ("koru.observability_events", "emit_verify"),
}

HOOK_NAMES: frozenset[str] = frozenset(_HOOK_SPECS)


def _default_hook(name: str) -> Callable[..., Any]:
    module_name, attr = _HOOK_SPECS[name]

    def _call(*args: Any, **kwargs: Any) -> Any:
        try:
            impl = getattr(importlib.import_module(module_name), attr)
        except ImportError:
            # Standalone koruide host: koru is not installed — soft no-op.
            return None
        return impl(*args, **kwargs)

    _call.__name__ = name
    _call.__qualname__ = f"host_hooks.{name}"
    _call.__doc__ = (
        f"Default koruide host hook: forwards to ``{module_name}.{attr}`` "
        "when koru is importable, otherwise no-ops."
    )
    return _call


record_integration_action: Callable[..., Any] = _default_hook("record_integration_action")
plugin_socket_command: Callable[..., Any] = _default_hook("plugin_socket_command")
emit_action: Callable[..., Any] = _default_hook("emit_action")
emit_decision: Callable[..., Any] = _default_hook("emit_decision")
emit_failure: Callable[..., Any] = _default_hook("emit_failure")
emit_intent: Callable[..., Any] = _default_hook("emit_intent")
emit_phase: Callable[..., Any] = _default_hook("emit_phase")
emit_verify: Callable[..., Any] = _default_hook("emit_verify")


def set_host_hooks(**hooks: Callable[..., Any]) -> None:
    """Install host implementations for the named hooks.

    Unknown hook names raise ``ValueError`` so typos fail loudly at wiring
    time rather than silently leaving a default in place.
    """
    unknown = sorted(set(hooks) - HOOK_NAMES)
    if unknown:
        raise ValueError(f"unknown koruide host hooks: {unknown}")
    globals().update(hooks)


def reset_host_hooks() -> None:
    """Restore the lazy defaults for every hook (test helper)."""
    for name in _HOOK_SPECS:
        globals()[name] = _default_hook(name)


__all__ = [
    "HOOK_NAMES",
    "emit_action",
    "emit_decision",
    "emit_failure",
    "emit_intent",
    "emit_phase",
    "emit_verify",
    "plugin_socket_command",
    "record_integration_action",
    "reset_host_hooks",
    "set_host_hooks",
]
