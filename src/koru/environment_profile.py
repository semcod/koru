"""Resolved environment profile for Koru autonomy decisions.

The autonomy loop should not treat ``ide=vscodium`` as a magic string that
implicitly means "Wayland + VS Code-family VSIX + host-click submit + OpenAI".
Those are separate axes. This module makes the axes explicit so each IDE, LLM
backend, OS/session, and control transport can evolve independently.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from koru.interface_registry import InterfaceDescriptor, get_interface_descriptor
from koruide.ides.registry import get_strategy
from koru.autopilot.ide import detect_running_ides, detect_terminal_host_ide_id, normalize_ide_id
from koruide.ide import detect_focused_ide_id


@dataclass(frozen=True)
class OsEnvironment:
    system: str
    platform: str
    session: str
    display_server: str
    preferred_keyboard_interface: str


@dataclass(frozen=True)
class IdeEnvironment:
    id: str
    label: str
    plugin_supported: bool
    trusted_publisher_required: bool
    strict_plugin_ack_required: bool
    keyboard_fallback_default: bool
    submit_key: str
    config_path: str | None
    extensions_metadata_path: str | None


@dataclass(frozen=True)
class LlmEnvironment:
    provider: str
    model: str | None
    source: str


@dataclass(frozen=True)
class ControlEnvironment:
    interface_id: str
    family: str
    transport: str
    write_mode: str
    verification_mode: str
    can_confirm_submit: bool
    operator_recovery: tuple[str, ...]


@dataclass(frozen=True)
class EnvironmentProfile:
    schema: str
    project: str
    os: OsEnvironment
    ide: IdeEnvironment
    llm: LlmEnvironment
    control: ControlEnvironment
    decision_key: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _session_name() -> str:
    from gillm.focus import resolve_active_os_strategy

    strategy = resolve_active_os_strategy()
    if strategy.id == "linux-wayland":
        return "wayland"
    if strategy.id == "linux-x11":
        return "x11"
    if strategy.id == "darwin":
        return "darwin"
    if strategy.id == "windows":
        return "windows"
    if os.environ.get("WAYLAND_DISPLAY", "").strip():
        return "wayland"
    if os.environ.get("DISPLAY", "").strip():
        return "x11"
    return "unknown"


def _preferred_keyboard_interface(session: str) -> str:
    from gillm.focus import resolve_active_os_strategy

    caps = resolve_active_os_strategy().capabilities()
    tool = caps.keyboard_tool
    if tool == "xdotool":
        return "os_injector_xdotool"
    if tool == "wtype":
        # GNOME Wayland lacks virtual-keyboard-v1; wtype silently no-ops.
        # Prefer ydotool when the daemon is available.
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        if "gnome" in desktop and shutil.which("ydotool") is not None:
            return "os_injector_ydotool"
        return "os_injector_wtype"
    if tool == "ydotool":
        return "os_injector_ydotool"
    key = session.strip().lower()
    if key == "x11":
        return "os_injector_xdotool"
    if key == "wayland":
        return "os_injector_wtype"
    return "os_injector_ydotool"


def resolve_os_environment() -> OsEnvironment:
    session = _session_name()
    return OsEnvironment(
        system=platform.system() or sys.platform,
        platform=sys.platform,
        session=session,
        display_server=session,
        preferred_keyboard_interface=_preferred_keyboard_interface(session),
    )


def _resolve_ide_id(raw: str | None) -> str:
    requested = normalize_ide_id(raw or "") or "auto"
    if requested != "auto":
        return requested
    # Prioritize focused IDE over environment variables for better detection
    focused = normalize_ide_id(detect_focused_ide_id())
    if focused:
        return focused
    for env_key in ("KORU_AUTOPILOT_IDE", "KORU_AUTOPILOT_INSTANCE"):
        from_env = normalize_ide_id(os.environ.get(env_key))
        if from_env:
            return from_env
    terminal = normalize_ide_id(detect_terminal_host_ide_id())
    if terminal:
        return terminal
    running = detect_running_ides()
    return running[0].id if running else "unknown"


def resolve_ide_environment(ide: str | None = "auto") -> IdeEnvironment:
    ide_id = _resolve_ide_id(ide)
    strategy = get_strategy(ide_id)
    if strategy is None:
        return IdeEnvironment(
            id=ide_id,
            label=ide_id,
            plugin_supported=False,
            trusted_publisher_required=False,
            strict_plugin_ack_required=False,
            keyboard_fallback_default=True,
            submit_key="Return",
            config_path=None,
            extensions_metadata_path=None,
        )
    settings = strategy.user_settings_path()
    extensions = strategy.extensions_metadata_path()
    return IdeEnvironment(
        id=strategy.id,
        label=strategy.label,
        plugin_supported=strategy.plugin.supports_vscode_extension,
        trusted_publisher_required=strategy.plugin.requires_trusted_publisher,
        strict_plugin_ack_required=strategy.plugin.strict_plugin_ack_required,
        keyboard_fallback_default=strategy.keyboard.keyboard_fallback_default,
        submit_key=strategy.keyboard.submit_key,
        config_path=str(settings) if settings else None,
        extensions_metadata_path=str(extensions) if extensions else None,
    )


def resolve_llm_environment() -> LlmEnvironment:
    from korullm.strategies.registry import resolve_llm_strategy_from_environment

    _strategy, resolved = resolve_llm_strategy_from_environment()
    return LlmEnvironment(
        provider=resolved.provider,
        model=resolved.model,
        source=resolved.source,
    )


def _control_interface_id(ide: IdeEnvironment, os_env: OsEnvironment) -> str:
    if ide.id == "antigravity":
        return "antigravity_native_send"
    if ide.id == "windsurf":
        return "windsurf_native_send"
    if ide.plugin_supported and not ide.keyboard_fallback_default:
        return "plugin_socket_vscode_family"
    if ide.id == "jetbrains":
        return "plugin_socket_jetbrains"
    return os_env.preferred_keyboard_interface


def _control_from_descriptor(interface_id: str) -> ControlEnvironment:
    descriptor: InterfaceDescriptor | None = get_interface_descriptor(interface_id)
    if descriptor is None:
        return ControlEnvironment(
            interface_id=interface_id,
            family="unknown",
            transport="unknown",
            write_mode="unknown",
            verification_mode="unknown",
            can_confirm_submit=False,
            operator_recovery=(),
        )
    return ControlEnvironment(
        interface_id=descriptor.id,
        family=descriptor.family,
        transport=descriptor.transport,
        write_mode=descriptor.write_mode,
        verification_mode=descriptor.verification.mode,
        can_confirm_submit=descriptor.verification.can_confirm_submit,
        operator_recovery=descriptor.operator_recovery,
    )


def resolve_environment_profile(
    project: Path,
    *,
    ide: str | None = "auto",
) -> EnvironmentProfile:
    os_env = resolve_os_environment()
    ide_env = resolve_ide_environment(ide)
    llm_env = resolve_llm_environment()
    control = _control_from_descriptor(_control_interface_id(ide_env, os_env))
    decision_key = "|".join(
        (
            f"os={os_env.display_server}",
            f"ide={ide_env.id}",
            f"llm={llm_env.provider}",
            f"control={control.interface_id}",
            f"verify={control.verification_mode}",
        )
    )
    return EnvironmentProfile(
        schema="koru.environment-profile/v1",
        project=str(project.resolve()),
        os=os_env,
        ide=ide_env,
        llm=llm_env,
        control=control,
        decision_key=decision_key,
    )


def environment_profile_payload(project: Path, *, ide: str | None = "auto") -> dict[str, object]:
    return resolve_environment_profile(project, ide=ide).to_dict()


__all__ = [
    "ControlEnvironment",
    "EnvironmentProfile",
    "IdeEnvironment",
    "LlmEnvironment",
    "OsEnvironment",
    "environment_profile_payload",
    "resolve_environment_profile",
    "resolve_ide_environment",
    "resolve_llm_environment",
    "resolve_os_environment",
]
