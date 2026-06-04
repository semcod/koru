"""Guardrails: shared code lives in gillm/sllm, not duplicated in koru."""

from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

import pytest


def test_autopilot_config_is_gillm_canonical() -> None:
    koruide_config = importlib.import_module("koruide.config")
    gillm_config = importlib.import_module("gillm.config")
    assert koruide_config.load_config is gillm_config.load_config
    assert koruide_config.cached_config is gillm_config.cached_config
    assert koruide_config.AutopilotConfig is gillm_config.AutopilotConfig


def test_koru_injection_shims_point_at_gillm() -> None:
    os_injector = importlib.import_module("koru.autopilot.os_injector")
    injector = importlib.import_module("koru.autopilot.injector")
    gillm_os = importlib.import_module("gillm.injection.os_injector")
    gillm_inj = importlib.import_module("gillm.injection.injector")
    assert os_injector is gillm_os
    assert injector is gillm_inj


def test_no_duplicate_injector_implementation_in_koru_src() -> None:
    root = Path(__file__).resolve().parents[1] / "src"
    forbidden = [
        root / "koru" / "autopilot" / "injector.py",
        root / "koru" / "autopilot" / "os_injector.py",
    ]
    for path in forbidden:
        text = path.read_text(encoding="utf-8")
        assert "gillm.injection" in text
        assert "class Injector" not in text
        assert "def inject_with_profile" not in text


def test_gillm_recovery_bridge_delegates_to_gillm() -> None:
    pytest.importorskip("gillm.recovery")
    recovery = importlib.import_module("koru.ide_adapters.gillm_recovery")
    gillm_recovery = importlib.import_module("gillm.recovery")
    assert recovery.diagnose_drive_reply is gillm_recovery.diagnose_drive_reply
    assert recovery.recovery_hints_for_reload is gillm_recovery.recovery_hints_for_reload


def test_autopilot_injector_shims_emit_deprecation_warning() -> None:
    import sys

    for name in (
        "koru.autopilot.injector",
        "koru.autopilot.os_injector",
    ):
        sys.modules.pop(name, None)
    with pytest.warns(DeprecationWarning, match="koru.autopilot.injector is deprecated"):
        importlib.import_module("koru.autopilot.injector")
    sys.modules.pop("koru.autopilot.os_injector", None)
    with pytest.warns(DeprecationWarning, match="koru.autopilot.os_injector is deprecated"):
        importlib.import_module("koru.autopilot.os_injector")


def test_koru_autopilot_cli_imports_gillm_injection_directly() -> None:
    cli_command = importlib.import_module("koru.autopilot.cli_command")
    doctor_cli = importlib.import_module("koru.autopilot.doctor_cli")
    direct_drive = importlib.import_module("koru.autopilot.cli_direct_drive")
    gillm_injector = importlib.import_module("gillm.injection.injector")
    assert cli_command.Injector is gillm_injector.Injector
    assert doctor_cli.Injector is gillm_injector.Injector
    assert direct_drive.Injector is gillm_injector.Injector


def test_koru_src_does_not_import_koruos() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "koru"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if path.name in {"injector.py", "os_injector.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "koruos" in text:
            offenders.append(str(path.relative_to(root.parent.parent)))
    assert offenders == []


def test_koruide_injection_shims_emit_deprecation_warning() -> None:
    import sys

    for name in (
        "koruide.injector",
        "koruide.os_injector",
        "koruide.injector_errors",
        "koruide.injector_backends",
    ):
        sys.modules.pop(name, None)
    with pytest.warns(DeprecationWarning, match="koruide.injector is deprecated"):
        importlib.import_module("koruide.injector")
    sys.modules.pop("koruide.os_injector", None)
    with pytest.warns(DeprecationWarning, match="koruide.os_injector is deprecated"):
        importlib.import_module("koruide.os_injector")


def test_koruos_shim_redirects_to_gillm_focus() -> None:
    import sys

    for name in list(sys.modules):
        if name == "koruos" or name.startswith("koruos."):
            del sys.modules[name]
    with pytest.warns(DeprecationWarning, match="koruos is deprecated"):
        koruos = importlib.import_module("koruos")
        wayland = importlib.import_module("koruos.strategies.wayland_linux")
    gillm_focus = importlib.import_module("gillm.focus")
    gillm_wayland = importlib.import_module("gillm.focus.wayland")
    assert koruos is gillm_focus
    assert wayland is gillm_wayland
    assert wayland.WaylandLinuxStrategy.__module__.startswith("gillm.focus")


def test_koruos_import_emits_deprecation_warning() -> None:
    for name in list(sys.modules):
        if name == "koruos" or name.startswith("koruos."):
            del sys.modules[name]
    with pytest.warns(DeprecationWarning, match="koruos is deprecated"):
        importlib.import_module("koruos")


def test_sllm_bridge_delegates_shell_drive_to_sillm() -> None:
    bridge = importlib.import_module("koru.sllm_bridge")
    source = inspect.getsource(bridge.drive_shell_chat)
    assert "drive_koru_chat" in source
    assert "sillm.compat" in source
