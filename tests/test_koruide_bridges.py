"""Bridge-module tests for `koruide` extraction phase."""

from __future__ import annotations

from koru.autopilot import daemon as legacy_daemon_mod
from koru.autopilot import ide as legacy_ide_mod
from koru.autopilot import injector as legacy_injector_mod
from koru.autopilot import os_injector as legacy_os_injector_mod
from koruide import daemon as koruide_daemon_mod
from koruide import ide as koruide_ide_mod
from koruide import injector as koruide_injector_mod
from koruide import os_injector as koruide_os_injector_mod


def test_koruide_ide_bridge_exports_legacy_symbols() -> None:
    assert koruide_ide_mod.RunningIDE is legacy_ide_mod.RunningIDE
    assert koruide_ide_mod.pick_target is legacy_ide_mod.pick_target
    assert koruide_ide_mod.detect_running_ides_cached is legacy_ide_mod.detect_running_ides_cached


def test_koruide_injector_bridge_exports_legacy_symbols() -> None:
    assert koruide_injector_mod.Injector is legacy_injector_mod.Injector
    assert koruide_injector_mod.InjectorError is legacy_injector_mod.InjectorError
    assert koruide_injector_mod.InjectionResult is legacy_injector_mod.InjectionResult


def test_koruide_os_injector_bridge_exports_legacy_symbols() -> None:
    assert koruide_os_injector_mod.OsInjectorError is legacy_os_injector_mod.OsInjectorError
    assert koruide_os_injector_mod.load_profile is legacy_os_injector_mod.load_profile
    assert koruide_os_injector_mod.inject_with_profile is legacy_os_injector_mod.inject_with_profile
    assert koruide_os_injector_mod.try_drive_with_profile is legacy_os_injector_mod.try_drive_with_profile


def test_autopilot_daemon_shim_points_to_koruide_implementation() -> None:
    assert legacy_daemon_mod.AutopilotDaemon is koruide_daemon_mod.AutopilotDaemon
    assert legacy_daemon_mod._default_handoff is koruide_daemon_mod._default_handoff
