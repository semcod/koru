"""`koruide` — native IDE control-plane package.

Extracted from ``koru.autopilot``.  Each submodule listed below was
originally part of the legacy autopilot package and now lives here as
the canonical implementation.
"""

from __future__ import annotations

import sys  # noqa: F401

try:
    import gillm.injection.errors as _errors  # noqa: F401
    import gillm.injection.os_injector as _os_injector
    from gillm.injection.errors import InjectorError
    from gillm.injection.injector import Injector
    from gillm.injection.os_injector import (
        OsInjectorError,
        inject_with_profile,
        load_profile,
        try_drive_with_profile,
    )
except ImportError:  # degraded host: keep koruide importable; actuation soft-fails
    _os_injector = None

    class InjectorError(Exception):  # type: ignore[no-redef]
        """Raised when gillm's injection stack is unavailable on this host."""

    class OsInjectorError(InjectorError):  # type: ignore[no-redef]
        """Raised when gillm's OS injector is unavailable on this host."""

    class Injector:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs) -> None:
            raise InjectorError(
                "gillm is not installed; keyboard/GUI injection unavailable "
                "(pip install gillm)"
            )

    def _gillm_missing(*_args, **_kwargs):
        raise OsInjectorError(
            "gillm is not installed; keyboard/GUI injection unavailable "
            "(pip install gillm)"
        )

    inject_with_profile = _gillm_missing  # type: ignore[assignment]
    load_profile = _gillm_missing  # type: ignore[assignment]
    try_drive_with_profile = _gillm_missing  # type: ignore[assignment]

from .audit import AuditLog, default_log_path
from .client import KoruIDEClient, build_client
from .ide import RunningIDE, detect_focused_ide_id, detect_running_ides, pick_target
from .plugin_installer import (
    PluginInstallResult,
    format_plugin_install_result,
    install_plugin_for_ide,
)
from .ports import (
    ChatMessage,
    DriveOutcome,
    IdeChatHistoryPort,
    IdeChatPort,
    IdeLifecyclePort,
)
from .protocol import (
    MAX_LINE_BYTES,
    Message,
    ProtocolError,
    ack,
    chat_send,
    decode,
    error,
)
from .socket import default_socket_path


def _koru_activity_warn_bridge(message: str, *, hint: str | None = None, **kwargs) -> None:
    from koru.activity_log import activity_warn

    activity_warn(message, hint=hint, **kwargs)


if _os_injector is not None:
    _os_injector.emit_activity_warn = _koru_activity_warn_bridge


# Lazy exports (STARTER-563): ``.daemon``, ``.config`` and ``.host_setup``
# import gillm (and the daemon hooks back into koru via
# ``koruide.host_hooks``) at module level, so they are resolved on first
# attribute access to keep ``import koruide`` working on standalone hosts
# without gillm/koru installed.
_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "AutopilotDaemon": (".daemon", "AutopilotDaemon"),
    "AutopilotConfig": (".config", "AutopilotConfig"),
    "cached_config": (".config", "cached_config"),
    "clear_config_cache": (".config", "clear_config_cache"),
    "load_config": (".config", "load_config"),
    "build_setup_host_report": (".host_setup", "build_setup_host_report"),
    "install_ydotoold_user_service": (".host_setup", "install_ydotoold_user_service"),
    "run_host_setup": (".host_setup", "run_host_setup"),
}


def __getattr__(name: str):
    spec = _LAZY_EXPORTS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr = spec
    from importlib import import_module

    value = getattr(import_module(module_name, __name__), attr)
    globals()[name] = value  # cache: later access bypasses __getattr__
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))


__all__ = [
    "AuditLog",
    "AutopilotConfig",
    "AutopilotDaemon",
    "ChatMessage",
    "DriveOutcome",
    "IdeChatHistoryPort",
    "IdeChatPort",
    "IdeLifecyclePort",
    "Injector",
    "InjectorError",
    "KoruIDEClient",
    "MAX_LINE_BYTES",
    "Message",
    "OsInjectorError",
    "PluginInstallResult",
    "ProtocolError",
    "RunningIDE",
    "ack",
    "build_client",
    "build_setup_host_report",
    "cached_config",
    "chat_send",
    "clear_config_cache",
    "decode",
    "default_log_path",
    "default_socket_path",
    "detect_focused_ide_id",
    "detect_running_ides",
    "error",
    "format_plugin_install_result",
    "inject_with_profile",
    "install_plugin_for_ide",
    "install_ydotoold_user_service",
    "load_config",
    "load_profile",
    "pick_target",
    "run_host_setup",
    "try_drive_with_profile",
]
