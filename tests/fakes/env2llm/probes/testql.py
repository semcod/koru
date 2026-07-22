from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def testql_available() -> bool:
    try:
        import testql  # noqa: F401

        return True
    except ImportError:
        return False


def discover_scenario_files(project_dir: Path | str) -> list[dict[str, Any]]:
    root = Path(project_dir).resolve()
    patterns = ("*.testql.toon.yaml", "*.testql.less", "*.oql", "*.tql")
    found: list[dict[str, Any]] = []
    for pattern in patterns:
        for path in sorted(root.rglob(pattern)):
            if any(part.startswith(".") for part in path.relative_to(root).parts):
                continue
            found.append(
                {
                    "path": str(path.relative_to(root)),
                    "format": path.suffixes[-2:] if path.name.endswith(".testql.toon.yaml") else [path.suffix],
                    "name": path.stem,
                }
            )
    return found[:64]


def collect_testql_catalog(project_dir: Path | str | None = None) -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []
    if project_dir is not None:
        scenarios = discover_scenario_files(project_dir)

    playwright = False
    if testql_available():
        playwright = importlib.util.find_spec("playwright") is not None

    return {
        "available": testql_available(),
        "playwright": playwright,
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "files": [row["path"] for row in scenarios],
    }
