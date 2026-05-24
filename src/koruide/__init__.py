"""`koruide` — native IDE control-plane package.

Extracted from ``koru.autopilot``.  Each submodule listed below was
originally part of the legacy autopilot package and now lives here as
the canonical implementation.
"""

from __future__ import annotations

from .audit import AuditLog, default_log_path
from .client import KoruIDEClient, build_client
from .config import AutopilotConfig, cached_config, clear_config_cache, load_config
from .daemon import AutopilotDaemon
from .host_setup import build_setup_host_report, install_ydotoold_user_service, run_host_setup
from .ide import RunningIDE, detect_focused_ide_id, detect_running_ides, pick_target
from .injector import Injector, InjectorError
from .os_injector import OsInjectorError, inject_with_profile, load_profile, try_drive_with_profile
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
