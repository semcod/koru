from __future__ import annotations

from pathlib import Path
from typing import Any
import time


def mark_capture_fresh(path: Path | str) -> None:
    return None


def sync_vql_cache_with_image(*_args, **_kwargs) -> list:
    return []


def capture_sidecar_path(image: Path | str) -> Path:
    p = Path(image)
    return p.parent / (p.stem + p.suffix + ".captured_at")


def clear_vql_cache(image: Path | str) -> list[Path]:
    paths = vql_cache_paths(Path(image))
    removed: list[Path] = []
    for p in paths:
        if p.exists():
            try:
                p.unlink()
                removed.append(p)
            except Exception:
                pass
    return removed


def image_freshness(image: Path | str) -> dict[str, Any]:
    p = Path(image)
    sidecar = capture_sidecar_path(p)
    if sidecar.exists():
        return {"is_fresh": True, "capture_source": "sidecar"}
    try:
        mtime = p.stat().st_mtime
    except Exception:
        return {"is_fresh": False, "capture_source": "missing"}
    max_age = max_image_age_seconds()
    is_fresh = (time.time() - mtime) < max_age
    return {"is_fresh": is_fresh, "capture_source": "file", "age_seconds": time.time() - mtime}


def max_image_age_seconds() -> int:
    return 3600


def verify_capture_updated(image: Path | str, *, previous_ts: float | None = None) -> bool:
    p = Path(image)
    try:
        return p.stat().st_mtime > (previous_ts or 0)
    except Exception:
        return False


def vql_cache_paths(image: Path | str) -> list[Path]:
    p = Path(image)
    stem = p.stem
    return [p.parent / f"{stem}.vql.imgl.json", p.parent / f"{stem}.vql.json"]
