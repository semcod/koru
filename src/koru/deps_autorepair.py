"""Runtime auto-install for optional Koru / desktop dependencies."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from collections.abc import Sequence

# Top-level import name -> pip requirement
MODULE_PIP_SPECS: dict[str, str] = {
    "env2llm": "env2llm[mqtt]>=0.1.10",
    "vdisplay": "vdisplay>=0.1.8",
    "nlp2uri": "nlp2uri[envmap]>=0.4.7",
    "testql": "testql>=1.2.55",
    "gillm": "gillm>=0.1.9",
    "yaml": "pyyaml>=6.0,<7.0",
    "pytesseract": "pytesseract>=0.3.10",
    "PIL": "Pillow>=10.0",
}

# Koru optional extra groups (from pyproject.toml)
EXTRA_PIP_SPECS: dict[str, list[str]] = {
    "desktop": [
        "nlp2uri[envmap]>=0.4.7",
        "env2llm[mqtt]>=0.1.10",
        "testql>=1.2.55",
    ],
    "vdisplay": ["vdisplay>=0.1.8"],
    "vision": ["Pillow>=10.0", "pytesseract>=0.3.10"],
}


def auto_install_enabled() -> bool:
    raw = os.environ.get("KORU_AUTO_INSTALL_DEPS", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def module_importable(module: str) -> bool:
    try:
        importlib.import_module(module)
        return True
    except ImportError:
        return False


def pip_install(specs: Sequence[str], *, label: str = "koru") -> int:
    unique = []
    seen: set[str] = set()
    for spec in specs:
        text = str(spec).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    if not unique:
        return 0
    cmd = [sys.executable, "-m", "pip", "install", *unique]
    print(f"{label}: installing missing packages: {', '.join(unique)}", file=sys.stderr)
    print(f"{label}: $ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.call(cmd)  # noqa: S603 — user-invoked repair


def ensure_modules(
    *modules,
    label: str = "koru",
    install: bool | None = None,
) -> bool:
    """Import modules, optionally pip-installing missing ones first."""
    missing = [name for name in modules if not module_importable(name)]
    if not missing:
        return True
    if install is None:
        install = auto_install_enabled()
    if not install:
        return False

    specs = [MODULE_PIP_SPECS.get(name, name) for name in missing]
    print(
        f"{label}: missing Python packages ({', '.join(missing)}) — attempting auto-install...",
        file=sys.stderr,
    )
    rc = pip_install(specs, label=label)
    if rc != 0:
        print(f"{label}: auto-install failed (exit {rc})", file=sys.stderr)
        return False

    still_missing = [name for name in missing if not module_importable(name)]
    if still_missing:
        print(
            f"{label}: still missing after install: {', '.join(still_missing)}",
            file=sys.stderr,
        )
        return False
    print(f"{label}: auto-install OK ({', '.join(missing)})", file=sys.stderr)
    return True


def ensure_extra(extra: str, *, label: str = "koru", install: bool | None = None) -> bool:
    specs = EXTRA_PIP_SPECS.get(extra)
    if not specs:
        return False
    modules = {
        "desktop": ("env2llm", "nlp2uri", "testql"),
        "vdisplay": ("vdisplay",),
    }.get(extra, ())
    if modules and all(module_importable(name) for name in modules):
        return True
    if install is None:
        install = auto_install_enabled()
    if not install:
        return False
    print(f"{label}: installing optional extra [{extra}]...", file=sys.stderr)
    rc = pip_install(specs, label=label)
    if rc != 0:
        return False
    modules = {
        "desktop": ("env2llm", "nlp2uri", "testql"),
        "vdisplay": ("vdisplay",),
    }.get(extra, ())
    return all(module_importable(name) for name in modules) if modules else True


def ensure_desktop_stack(*, label: str = "koru") -> bool:
    """env2llm + nlp2uri + testql used by calibration/registry."""
    ok = ensure_extra("desktop", label=label)
    if ok:
        return True
    return ensure_modules("env2llm", "nlp2uri", "testql", label=label)


def ensure_vdisplay_runtime(*, label: str = "koru") -> bool:
    if module_importable("vdisplay"):
        return True
    if ensure_modules("vdisplay", label=label):
        return module_importable("vdisplay")
    return ensure_extra("vdisplay", label=label)


def ensure_vision_ocr(*, label: str = "koru") -> bool:
    """Pillow + pytesseract (+ system tesseract) for post-drive OCR verify."""
    if ensure_extra("vision", label=label):
        return True
    return ensure_modules("PIL", "pytesseract", label=label)
