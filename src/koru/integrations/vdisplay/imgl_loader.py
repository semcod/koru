"""imgl/vdisplay CLI discovery, import machinery and subprocess env extracted
from ``vdisplay_client``.

Moved verbatim from the historical ``vdisplay_client`` monolith; the
facade re-exports every name, so ``from koru.integrations.vdisplay_client
import X`` keeps working. References that were ``vdisplay_client`` module
globals resolve through the facade at call time (``_vdc()``) so
``monkeypatch.setattr(vdisplay_client, ...)`` keeps steering the pipeline.
"""

from __future__ import annotations

import os
from pathlib import Path


def _vdc():
    """The vdisplay_client facade (imported lazily: it imports this module)."""
    import koru.integrations.vdisplay_client as m

    return m


def _real_imgl_src() -> str | None:
    """Filesystem path to a semcod imgl checkout, when one is available."""
    candidates: list[str] = []
    explicit = os.environ.get("IMGL_SRC", "").strip()
    if explicit:
        candidates.append(explicit)
    candidates.append(str(Path.home() / "github/semcod/imgl"))
    for raw in candidates:
        root = Path(raw).expanduser()
        if (root / "imgl" / "pipeline.py").is_file() or (root / "imgl" / "config.py").is_file():
            return str(root)
    return None


def _ensure_real_imgl_on_path() -> None:
    """Prefer an explicit semcod imgl checkout over an installed package."""
    import sys

    imgl_root = _vdc()._real_imgl_src()
    if not imgl_root:
        return
    if imgl_root in sys.path:
        sys.path.remove(imgl_root)
    sys.path.insert(0, imgl_root)
    cached = sys.modules.get("imgl")
    cached_file = str(getattr(cached, "__file__", "") or "") if cached is not None else ""
    cached_path = Path(cached_file).resolve() if cached_file else None
    root_path = Path(imgl_root).resolve()
    if cached is not None and (
        cached_path is None or root_path not in cached_path.parents
    ):
        for name in list(sys.modules):
            if name == "imgl" or name.startswith("imgl."):
                sys.modules.pop(name, None)


def _vdisplay_cli_candidates() -> list[str]:
    import shutil

    out: list[str] = []
    for candidate in (
        os.environ.get("VDISPLAY_CLI", "").strip(),
        str(Path.home() / "github/wronai/vdisplay/.venv/bin/vdisplay"),
        shutil.which("vdisplay") or "",
        str(Path.home() / ".venv/bin/vdisplay"),
    ):
        if candidate and Path(candidate).is_file() and candidate not in out:
            out.append(candidate)
    if not out:
        out.append("vdisplay")
    return out


def _vdisplay_cli_path() -> str:
    for candidate in _vdc()._vdisplay_cli_candidates():
        return candidate
    return "vdisplay"


def _vdisplay_observe_python_candidates() -> list[str]:
    import sys

    out: list[str] = []
    for candidate in (
        os.environ.get("VDISPLAY_OBSERVE_PYTHON", "").strip(),
        str(Path.home() / ".venv/bin/python"),
        str(Path.home() / "github/wronai/vdisplay/.venv/bin/python"),
        sys.executable,
    ):
        if candidate and Path(candidate).is_file() and candidate not in out:
            out.append(candidate)
    if not out:
        out.append(sys.executable)
    return out


def _vdisplay_subprocess_env(*, ide: str = "auto") -> dict[str, str]:
    """Env for vdisplay CLI subprocess: real imgl first, capture validation for IDE."""
    env = os.environ.copy()
    try:
        from koru.integrations.vdisplay_agent_bootstrap import apply_vdisplay_agent_env

        apply_vdisplay_agent_env()
        env = os.environ.copy()
    except ImportError:
        pass
    path_parts: list[str] = []
    imgl_root = _vdc()._real_imgl_src()
    if imgl_root:
        path_parts.append(imgl_root)
    vdisplay_src = os.environ.get("VDISPLAY_SRC", "").strip()
    if not vdisplay_src:
        guess = Path.home() / "github/wronai/vdisplay/src"
        if guess.is_dir():
            vdisplay_src = str(guess)
    if vdisplay_src:
        path_parts.append(vdisplay_src)
    koru_src = os.environ.get("KORU_SRC", "").strip()
    if not koru_src:
        koru_src = str(Path(__file__).resolve().parents[2])
    if koru_src:
        path_parts.append(koru_src)
    existing = env.get("PYTHONPATH", "").strip()
    if existing:
        path_parts.append(existing)
    env["PYTHONPATH"] = ":".join(path_parts)
    env.setdefault("VDISPLAY_IMGL", "1")
    canon = _vdc()._canonical_ide(ide)
    if canon not in {"", "auto"}:
        env.setdefault("VDISPLAY_CAPTURE_VALIDATE_IDE", canon)
    return env


def _import_imgl_targets(name: str):
    """Import ``resolve_*`` from semcod imgl even when koru ships minimal ``imgl`` stubs."""
    target = _vdc()._import_imgl_target_via_stdlib(name)
    if target is not None:
        return target
    return _vdc()._import_imgl_target_from_source(name)


def _import_imgl_target_via_stdlib(name: str):
    """Resolve ``name`` from ``imgl.targets`` through the standard import machinery."""
    import importlib

    _vdc()._ensure_real_imgl_on_path()
    for _attempt in range(2):
        try:
            importlib.import_module("imgl.export.actuation_layers")
            mod = importlib.import_module("imgl.targets")
            if hasattr(mod, name):
                return getattr(mod, name)
        except ImportError:
            _vdc()._ensure_real_imgl_on_path()
    return None


def _load_light_module(module_name: str, path: Path):
    """Load a module from an explicit file path without triggering package import."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _install_imgl_source_packages(pkg_dir: Path):
    """Register hand-built ``imgl``/``imgl.export`` package modules in ``sys.modules``."""
    import sys
    import types

    pkg = types.ModuleType("imgl")
    pkg.__file__ = str(pkg_dir / "__init__.py")
    pkg.__path__ = [str(pkg_dir)]  # type: ignore[attr-defined]
    pkg.__package__ = "imgl"
    sys.modules["imgl"] = pkg
    export_pkg = types.ModuleType("imgl.export")
    export_pkg.__file__ = str(pkg_dir / "export" / "__init__.py")
    export_pkg.__path__ = [str(pkg_dir / "export")]  # type: ignore[attr-defined]
    export_pkg.__package__ = "imgl.export"
    sys.modules["imgl.export"] = export_pkg
    return pkg, export_pkg


def _import_imgl_target_from_source(name: str):
    """Resolve ``name`` by loading ``imgl.targets`` straight from the source tree."""
    import sys

    root = _vdc()._real_imgl_src()
    if not root:
        return None
    root_path = Path(root).resolve()
    pkg_dir = root_path / "imgl"
    targets_path = pkg_dir / "targets.py"
    actuation_path = pkg_dir / "export" / "actuation_layers.py"
    if not targets_path.is_file() or not actuation_path.is_file():
        return None
    for mod_name in list(sys.modules):
        if mod_name == "imgl" or mod_name.startswith("imgl."):
            sys.modules.pop(mod_name, None)
    pkg, export_pkg = _vdc()._install_imgl_source_packages(pkg_dir)
    actuation_mod = _vdc()._load_light_module("imgl.export.actuation_layers", actuation_path)
    if actuation_mod is None:
        return None
    export_pkg.actuation_layers = actuation_mod
    targets_mod = _vdc()._load_light_module("imgl.targets", targets_path)
    if targets_mod is None:
        return None
    pkg.targets = targets_mod
    return getattr(targets_mod, name, None)
