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
    assert calls == [["env2llm[mqtt]>=0.1.14"]]


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


def test_vdisplay_autorepair_uses_public_api_release_floor() -> None:
    from koru.deps_autorepair import EXTRA_PIP_SPECS, MODULE_PIP_SPECS

    assert MODULE_PIP_SPECS["vdisplay"] == "vdisplay>=0.1.58"
    assert EXTRA_PIP_SPECS["vdisplay"] == ["vdisplay>=0.1.58"]


def test_testql_autorepair_uses_public_runner_release_floor() -> None:
    from koru.deps_autorepair import EXTRA_PIP_SPECS, MODULE_PIP_SPECS

    assert MODULE_PIP_SPECS["testql"] == "testql>=1.2.62"
    assert "testql>=1.2.62" in EXTRA_PIP_SPECS["desktop"]


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

    def fake_load_public_api() -> bool:
        if not repair_calls:
            return False
        reg._ENV2LLM_AVAILABLE = True
        reg._ENV2LLM_IMPORT_ERROR = None
        reg._SERVICE_FACTORY = object()
        return True

    monkeypatch.setattr(reg, "_load_env2llm_api", fake_load_public_api)

    class FakeService:
        project_id = "demo"

        def refresh(self, **_kwargs):
            return None

        def registry_path(self):
            return Path("/tmp/reg.json")

        def desktop_payload(self):
            return {"ide_calibrations": []}

    class FakeDescriptor:
        def to_dict(self):
            return {
                "schema": "env2llm.service-descriptor.v1",
                "request_hash": "0" * 64,
                "descriptor_hash": "1" * 64,
            }

    built = (FakeService(), FakeDescriptor().to_dict())
    monkeypatch.setattr(reg, "_get_service", lambda **_kwargs: built)
    monkeypatch.setitem(
        sys.modules,
        "koruapi.calibration_validator",
        types.SimpleNamespace(validate_calibrations=lambda _desktop: {"ok": True}),
    )

    result = reg.env2llm_sync_after_calibration(project_dir="/tmp")
    assert repair_calls == ["koru calibrate"]
    assert result.get("ok") is True
    assert result["service_descriptor"]["schema"] == "env2llm.service-descriptor.v1"


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
