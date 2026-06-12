"""Bridge Koru MCP to TestQL GUI/DOM scenario runner."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_TESTQL_IMPORT_ERROR: str | None = None

try:
    import testql  # noqa: F401
    from testql.commands import run_cmd as _testql_run_cmd  # noqa: F401

    _TESTQL_AVAILABLE = True
except ImportError as exc:
    _TESTQL_AVAILABLE = False
    _TESTQL_IMPORT_ERROR = str(exc)


def testql_available() -> bool:
    return _TESTQL_AVAILABLE


def testql_missing_message() -> str:
    if _TESTQL_IMPORT_ERROR:
        return (
            f"testql is not installed ({_TESTQL_IMPORT_ERROR}). "
            "Install from: pip install -e /path/to/oqlos/testql"
        )
    return "testql is not installed."


def _resolve_root(project_dir: str | None = None, project_root: str | None = None) -> Path:
    raw = (
        project_dir
        or project_root
        or os.environ.get("KORU_PROJECT_ROOT")
        or "."
    )
    return Path(raw).resolve()


def testql_list_scenarios(
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
) -> dict[str, Any]:
    if not _TESTQL_AVAILABLE:
        return {"ok": False, "error": testql_missing_message()}
    try:
        from env2llm.probes.testql import collect_testql_catalog

        catalog = collect_testql_catalog(_resolve_root(project_dir, project_root))
        return {"ok": True, **catalog}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def testql_run_scenario(
    file_spec: str,
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    url: str = "http://localhost:8101",
    dry_run: bool = True,
    quiet: bool = True,
    timeout: int | None = None,
) -> dict[str, Any]:
    if not _TESTQL_AVAILABLE:
        return {"ok": False, "error": testql_missing_message()}
    try:
        from testql.commands.run_cmd import _resolve_input_paths, _run_single

        root = _resolve_root(project_dir, project_root)
        spec_path = Path(file_spec)
        resolved_spec = str(spec_path if spec_path.is_absolute() else root / file_spec)
        paths = _resolve_input_paths(resolved_spec)
        results = []
        for path in paths:
            result = _run_single(path, url, dry_run, quiet, timeout)
            results.append(
                {
                    "file": str(path),
                    "ok": bool(result.ok),
                    "passed": result.passed,
                    "failed": result.failed,
                    "steps": len(result.steps),
                    "duration_ms": round(result.duration_ms, 1),
                    "errors": result.errors,
                    "warnings": result.warnings,
                }
            )
        failed = sum(1 for item in results if not item["ok"])
        return {
            "ok": failed == 0,
            "files": len(results),
            "runs": results,
            "dry_run": dry_run,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
