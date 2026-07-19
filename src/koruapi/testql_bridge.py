"""Bridge Koru MCP to TestQL GUI/DOM scenario runner."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any

_TESTQL_IMPORT_ERROR: str | None = None
_TESTQL_API: Any = None

try:
    _TESTQL_API = importlib.import_module("testql.verification")

    _TESTQL_AVAILABLE = True
except ImportError as exc:
    _TESTQL_AVAILABLE = False
    _TESTQL_IMPORT_ERROR = str(exc)


def testql_available() -> bool:
    return _TESTQL_AVAILABLE


def testql_missing_message() -> str:
    if _TESTQL_IMPORT_ERROR:
        return f"testql is not installed ({_TESTQL_IMPORT_ERROR}). Install with: pip install 'testql>=1.2.62'"
    return "testql is not installed."


def _resolve_root(project_dir: str | None = None, project_root: str | None = None) -> Path:
    raw = project_dir or project_root or os.environ.get("KORU_PROJECT_ROOT") or "."
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
        request = _TESTQL_API.VerificationRequest(
            file_specs=(file_spec,),
            project_dir=_resolve_root(project_dir, project_root),
            url=url,
            dry_run=dry_run,
            quiet=quiet,
            timeout=timeout,
        )
        return _TESTQL_API.run_verification(request).to_dict()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
