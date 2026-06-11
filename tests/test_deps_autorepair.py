"""Tests for runtime dependency auto-install."""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path


def test_auto_install_disabled_by_env(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTO_INSTALL_DEPS", "0")
    from koru.deps_autorepair import auto_install_enabled, ensure_modules

    assert auto_install_enabled() is False
    assert ensure_modules("definitely_not_a_real_koru_module_xyz", install=None) is False


def test_ensure_modules_calls_pip_when_missing(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTO_INSTALL_DEPS", "1")
    calls: list[list[str]] = []
    installed: set[str] = set()

    def fake_importable(name: str) -> bool:
        return name in installed

    def fake_pip(specs, *, label="koru"):
        calls.append(list(specs))
        for spec in specs:
            installed.add(spec.split("[", 1)[0].split(">=")[0].split("==")[0])
        return 0

    monkeypatch.setattr("koru.deps_autorepair.pip_install", fake_pip)
    monkeypatch.setattr("koru.deps_autorepair.module_importable", fake_importable)

    from koru.deps_autorepair import ensure_modules

    assert ensure_modules("env2llm", label="test") is True
    assert calls == [["env2llm[mqtt]>=0.1.10"]]


def test_ensure_modules_skips_pip_when_present(monkeypatch) -> None:
    calls: list[list[str]] = []

    monkeypatch.setattr(
        "koru.deps_autorepair.pip_install",
        lambda specs, *, label="koru": calls.append(list(specs)) or 0,
    )
    monkeypatch.setattr("koru.deps_autorepair.module_importable", lambda _name: True)

    from koru.deps_autorepair import ensure_modules

    assert ensure_modules("env2llm") is True
    assert calls == []


def _load_env2llm_registry_module():
    root = Path(__file__).resolve().parents[1] / "src"
    path = root / "koruapi" / "env2llm_registry.py"
    spec = importlib.util.spec_from_file_location("koru_env2llm_registry_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_env2llm_sync_attempts_autorepair(monkeypatch) -> None:
    repair_calls: list[str] = []

    monkeypatch.setattr(
        "koru.deps_autorepair.ensure_desktop_stack",
        lambda *, label="koru": repair_calls.append(label) or True,
    )

    reg = _load_env2llm_registry_module()
    reg._ENV2LLM_AVAILABLE = False
    reg._ENV2LLM_IMPORT_ERROR = "No module named 'env2llm'"

    class RegistryService:
        pass

    fake_pkg = types.ModuleType("env2llm.service.registry_service")
    fake_pkg.RegistryService = RegistryService
    monkeypatch.setitem(sys.modules, "env2llm.service.registry_service", fake_pkg)

    class FakeService:
        project_id = "demo"

        def refresh(self, **_kwargs):
            return None

        def registry_path(self):
            return Path("/tmp/reg.json")

        def desktop_payload(self):
            return {"ide_calibrations": []}

    monkeypatch.setattr(reg, "_get_service", lambda **_kwargs: FakeService())
    monkeypatch.setitem(
        sys.modules,
        "koruapi.calibration_validator",
        types.SimpleNamespace(validate_calibrations=lambda _desktop: {"ok": True}),
    )

    result = reg.env2llm_sync_after_calibration(project_dir="/tmp")
    assert repair_calls == ["koru calibrate"]
    assert result.get("ok") is True


def test_vdisplay_available_triggers_autorepair(monkeypatch) -> None:
    repair_calls: list[str] = []

    import koru.integrations.vdisplay_client as vc

    importlib.reload(vc)
    monkeypatch.setattr(vc, "_VDISPLAY_DIRECT", False)
    monkeypatch.setattr(vc, "_VDISPLAY_IMPORT_ERROR", "No module named 'vdisplay'")

    def fake_ensure(*, label="koru"):
        repair_calls.append(label)
        return True

    monkeypatch.setattr("koru.deps_autorepair.ensure_vdisplay_runtime", fake_ensure)
    monkeypatch.setattr(vc, "_reload_vdisplay_direct", lambda: True)
    monkeypatch.setattr(vc, "_agent_url", lambda: None)

    assert vc.vdisplay_available() is True
    assert repair_calls == ["koru drive"]
