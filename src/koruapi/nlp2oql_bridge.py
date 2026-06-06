"""Bridge Koru MCP to nlp2oql browser automation router."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_NLP2OQL_IMPORT_ERROR: str | None = None

try:
    import nlp2oql  # noqa: F401

    _NLP2OQL_AVAILABLE = True
except ImportError as exc:
    _NLP2OQL_AVAILABLE = False
    _NLP2OQL_IMPORT_ERROR = str(exc)


def nlp2oql_available() -> bool:
    return _NLP2OQL_AVAILABLE


def nlp2oql_missing_message() -> str:
    if _NLP2OQL_IMPORT_ERROR:
        return (
            f"nlp2oql is not installed ({_NLP2OQL_IMPORT_ERROR}). "
            "Install from: pip install -e /path/to/oqlos/nlp2oql"
        )
    return "nlp2oql is not installed."


def _resolve_root(project_dir: str | None = None, project_root: str | None = None) -> Path:
    raw = (
        project_dir
        or project_root
        or os.environ.get("KORU_PROJECT_ROOT")
        or "."
    )
    return Path(raw).resolve()


def nlp2oql_generate(
    prompt: str,
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    use_llm: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    if not _NLP2OQL_AVAILABLE:
        return {"ok": False, "error": nlp2oql_missing_message()}
    try:
        from nlp2oql import generate_scenario

        result = generate_scenario(
            prompt,
            project_dir=str(_resolve_root(project_dir, project_root)),
            use_llm=use_llm,
            validate=validate,
        )
        return {
            "ok": result.ok,
            "oql": result.oql,
            "planner": result.plan.planner,
            "validation": result.validation,
            "error": result.error,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def nlp2oql_run(
    prompt: str,
    *,
    project_dir: str | None = None,
    project_root: str | None = None,
    backend: str | None = None,
    execute: bool = False,
    url: str | None = None,
    captcha_solver: bool = False,
    visual_mode: bool = False,
) -> dict[str, Any]:
    if not _NLP2OQL_AVAILABLE:
        return {"ok": False, "error": nlp2oql_missing_message()}
    try:
        from nlp2oql import run_task

        result = run_task(
            prompt,
            project_dir=str(_resolve_root(project_dir, project_root)),
            backend=backend,
            execute=execute,
            url=url,
            captcha_solver=captcha_solver,
            visual_mode=visual_mode,
        )
        return {
            "ok": result.ok,
            "backend": result.backend,
            "reason": result.reason,
            "oql": result.oql,
            "execution": result.execution,
            "error": result.error,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
