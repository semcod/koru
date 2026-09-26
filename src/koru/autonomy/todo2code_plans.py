"""``t2c`` plan artifact discovery and plan-field normalization.

Locates the newest ``code-change-plans.json`` under a pipeline output
directory (``runs/*/`` layout or a flat test dump), checks artifact
freshness, loads the JSON plan set and normalizes the plan fields the
ticket filing needs (useful paths, dedupe keys, slugs, truncation).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from koru.autonomy.code_change_usefulness import plan_useful_paths

PLANS_FILENAME = "code-change-plans.json"


def find_latest_plans_path(out_dir: Path) -> Path | None:
    """Return the newest ``code-change-plans.json`` under ``out_dir/runs``."""
    runs = out_dir / "runs"
    if not runs.is_dir():
        # Also accept a flat dump for tests / manual runs.
        flat = out_dir / PLANS_FILENAME
        return flat if flat.is_file() else None
    candidates = sorted(
        runs.glob(f"*/{PLANS_FILENAME}"),
        key=lambda p: p.stat().st_mtime if p.is_file() else 0.0,
        reverse=True,
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def _plans_fresh(plans_path: Path, *, stale_minutes: float) -> bool:
    try:
        age_s = max(0.0, time.time() - plans_path.stat().st_mtime)
    except OSError:
        return False
    return age_s < stale_minutes * 60.0


def _load_plan_set(plans_path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(plans_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _string_list(value: Any) -> list[str]:
    return [str(v) for v in (value or []) if str(v).strip()]


def _truncate(text: str, limit: int = 140) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _plan_paths(plan: dict[str, Any]) -> list[str]:
    """Useful target paths only (venv/binary/analysis dumps filtered out)."""
    return plan_useful_paths(plan)


def _plan_dedupe_key(plan: dict[str, Any]) -> str:
    plan_id = str(plan.get("id") or "").strip()
    if plan_id:
        return f"todo2code:plan:{plan_id}"
    plan_hash = str(plan.get("planHash") or "").strip()
    if plan_hash:
        return f"todo2code:hash:{plan_hash}"
    title = _slug(str(plan.get("title") or "plan"))
    paths = ",".join(_plan_paths(plan)[:5])
    digest = hashlib.sha256(f"{title}|{paths}".encode()).hexdigest()[:16]
    return f"todo2code:fallback:{digest}"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]
