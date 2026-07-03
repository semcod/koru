"""Guard: every non-Python file under src/ must be declared in package-data.

Class of the 2026-07-03 ``korumesh/capture_host.html`` incident: a template
existed in the source tree, was loaded at runtime via ``importlib.resources``,
but was missing from ``[tool.setuptools.package-data]`` — so every installed
wheel crashed with FileNotFoundError while the repo checkout worked fine.

If this test fails for a new data file, either add a matching pattern to
``[tool.setuptools.package-data]`` in pyproject.toml (when the file must ship)
or add it to ``KNOWN_UNSHIPPED`` below with a short justification.
"""

from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# Files under src/ that intentionally do NOT ship in the wheel.
# Keep justified — an unexplained entry here recreates the incident.
KNOWN_UNSHIPPED: frozenset[str] = frozenset()

# Never data files: caches, bytecode, build metadata, runtime artifacts.
_IGNORED_SUFFIXES = (".pyc", ".pyo", ".orig", ".rej")
_IGNORED_DIR_MARKERS = ("__pycache__", ".egg-info")


def _package_data() -> dict[str, list[str]]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return pyproject["tool"]["setuptools"]["package-data"]


def _data_files() -> list[tuple[str, str]]:
    """(top-level package, relative path inside package) for each data file."""
    found: list[tuple[str, str]] = []
    for path in sorted(SRC.rglob("*")):
        if not path.is_file() or path.suffix == ".py":
            continue
        if path.suffix in _IGNORED_SUFFIXES:
            continue
        rel = path.relative_to(SRC)
        parts = rel.parts
        if any(marker in part for part in parts for marker in _IGNORED_DIR_MARKERS):
            continue
        if any(part.startswith(".") for part in parts):
            continue  # runtime artifact dirs like .koru/
        found.append((parts[0], str(Path(*parts[1:]))))
    return found


def test_every_src_data_file_ships_or_is_explicitly_excluded() -> None:
    package_data = _package_data()
    missing: list[str] = []
    for package, rel in _data_files():
        full = f"src/{package}/{rel}"
        if full in KNOWN_UNSHIPPED:
            continue
        patterns = package_data.get(package, [])
        if not any(fnmatch.fnmatch(rel, pattern) for pattern in patterns):
            missing.append(f"{full} (package '{package}' patterns: {patterns or 'NONE'})")
    assert not missing, (
        "data files present in src/ but not covered by "
        "[tool.setuptools.package-data] — installed wheels will not contain "
        "them (capture_host.html class of bug):\n  " + "\n  ".join(missing)
    )


def test_known_unshipped_entries_still_exist() -> None:
    """Prune KNOWN_UNSHIPPED when the excluded files disappear."""
    stale = [entry for entry in KNOWN_UNSHIPPED if not (ROOT / entry).is_file()]
    assert not stale, f"KNOWN_UNSHIPPED entries no longer exist, remove them: {stale}"
