"""Session-scoped autonomy artifacts under ``.vdisplay/YYYY-MM-DD/**``.

Each koru photo-VQL drive gets its own folder with observe → decide → act → verify
JSON sidecars so inference never mixes stale global captures with the current run.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def metadata_root() -> Path:
    return Path(os.environ.get("VDISPLAY_METADATA_DIR", ".vdisplay")).expanduser()


def vql_max_age_seconds() -> float:
    raw = os.environ.get("KORU_VDISPLAY_VQL_MAX_AGE_S", "300").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 300.0


def active_session_dir() -> Path | None:
    raw = os.environ.get("KORU_AUTONOMY_SESSION_DIR", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_dir() else None


def session_observe_paths(session_dir: Path | None = None) -> tuple[Path, Path]:
    root = session_dir or active_session_dir()
    if root is None:
        raise RuntimeError("no active autonomy session")
    observe = root / "observe"
    observe.mkdir(parents=True, exist_ok=True)
    png = observe / "capture.png"
    vql = observe / "capture.png.vql.json"
    return png, vql


def begin_autonomy_session(*, ide: str, source: str) -> Path:
    """Create ``.vdisplay/YYYY-MM-DD/ISO__koru-{ide}/`` and pin env for this run."""
    existing = active_session_dir()
    if existing is not None:
        return existing

    now = datetime.now(timezone.utc)
    date_dir = metadata_root() / now.strftime("%Y-%m-%d")
    ts = now.strftime("%Y-%m-%dT%H-%M-%SZ")
    slug = (ide or "auto").strip().lower().replace(" ", "-")[:32] or "auto"
    session_dir = date_dir / f"{ts}__koru-{slug}"
    session_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("observe", "decide", "act", "verify"):
        (session_dir / sub).mkdir(exist_ok=True)

    manifest = {
        "kind": "koru-autonomy-session",
        "started_at": now.isoformat(),
        "ide": ide,
        "source": source,
        "observe_dir": "observe",
        "decide_dir": "decide",
        "act_dir": "act",
        "verify_dir": "verify",
        "vql_max_age_s": vql_max_age_seconds(),
    }
    (session_dir / "session.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    os.environ["KORU_AUTONOMY_SESSION_DIR"] = str(session_dir.resolve())
    os.environ["VDISPLAY_SESSION_DIR"] = str(session_dir.resolve())
    os.environ.setdefault("VDISPLAY_SESSION", "1")
    os.environ.setdefault("VDISPLAY_SESSION_ID", f"koru-{slug}")

    png, vql = session_observe_paths(session_dir)
    os.environ["KORU_VDISPLAY_PHOTO_PATH"] = str(png.resolve())
    os.environ["KORU_VDISPLAY_VQL_PATH"] = str(vql.resolve())
    return session_dir


def append_session_index(session_dir: Path, *, phase: str, name: str, ok: bool | None) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "name": name,
        "ok": ok,
    }
    index_path = session_dir / "index.jsonl"
    with index_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def find_latest_koru_session(*, ide: str = "jetbrains", root: Path | None = None) -> Path | None:
    """Newest ``.vdisplay/YYYY-MM-DD/*__koru-{ide}/`` by session directory mtime."""
    base = root or metadata_root()
    if not base.is_dir():
        return None
    slug = (ide or "jetbrains").strip().lower().replace(" ", "-")[:32]
    pattern = f"*__koru-{slug}"
    candidates: list[Path] = []
    for child in base.iterdir():
        if not child.is_dir():
            continue
        candidates.extend(p for p in child.glob(pattern) if p.is_dir())
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def append_session_jsonl(session_dir: Path, rel_path: str, entry: dict[str, Any]) -> Path:
    """Append one JSON line under the session (e.g. act/cursor_positioning.jsonl)."""
    path = session_dir / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**entry, "ts": datetime.now(timezone.utc).isoformat()}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    return path


def persist_autonomy_phase(
    session_dir: Path,
    phase: str,
    name: str,
    payload: dict[str, Any],
) -> Path:
    phase_dir = session_dir / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    path = phase_dir / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    append_session_index(session_dir, phase=phase, name=name, ok=payload.get("ok"))
    return path


def _vql_load_capture_validation(vql_path: "Path") -> "dict[str, Any] | None":
    """Load capture_validation from VQL file metadata, or None on failure."""
    try:
        import json

        data = json.loads(vql_path.read_text(encoding="utf-8"))
        meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        cv = meta.get("capture_validation")
        return cv if isinstance(cv, dict) else None
    except Exception:
        return None


def vql_sidecar_is_stale(
    vql_path: Path,
    png_path: Path | None,
    *,
    ide: str = "auto",
    layer_count: int | None = None,
    window_mismatch: dict[str, Any] | None = None,
    capture_validation: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Return (stale, diagnostics). Stale sidecars must not feed decide/act."""
    reasons: list[str] = []
    now = time.time()
    max_age = vql_max_age_seconds()

    if not vql_path.is_file():
        return True, {"stale": True, "reasons": ["missing_vql"], "vql_path": str(vql_path)}

    vql_mt = vql_path.stat().st_mtime
    age_s = now - vql_mt
    info: dict[str, Any] = {
        "stale": False,
        "reasons": reasons,
        "vql_path": str(vql_path.resolve()),
        "vql_mtime": vql_mt,
        "age_s": round(age_s, 2),
        "max_age_s": max_age,
    }

    if capture_validation is None:
        capture_validation = _vql_load_capture_validation(vql_path)

    if max_age > 0 and age_s > max_age:
        reasons.append(f"vql_age_s>{max_age}")

    if png_path is not None:
        if not png_path.is_file():
            reasons.append("missing_png")
        else:
            png_mt = png_path.stat().st_mtime
            info["png_mtime"] = png_mt
            info["png_path"] = str(png_path.resolve())
            if max_age > 0 and (now - png_mt) > max_age:
                reasons.append(f"png_age_s>{max_age}")
            # Sidecar is written after screenshot — VQL mtime may be newer than PNG by seconds.
            # Stale only when VQL is older than PNG (sidecar not regenerated for this capture).
            if vql_mt + 2.0 < png_mt:
                reasons.append("vql_sidecar_older_than_png")
            elif png_mt > vql_mt + 600.0:
                reasons.append("png_newer_than_vql_by_600s")

    if layer_count is not None and layer_count == 0:
        reasons.append("empty_vql_layers")

    if window_mismatch is not None:
        reasons.append("ide_window_mismatch")
        info["ide_window_warning"] = window_mismatch
    elif isinstance(capture_validation, dict):
        info["capture_validation"] = capture_validation
        cv_reasons = capture_validation.get("reasons") or []
        expected = str(capture_validation.get("expected_ide") or "").strip()
        if expected and capture_validation.get("capture_confirmed") is False:
            reasons.append("capture_validation_failed")
            for item in cv_reasons:
                if item not in reasons:
                    reasons.append(str(item))

    info["stale"] = bool(reasons)
    info["reasons"] = reasons
    return bool(reasons), info


def copy_observe_artifacts_to_session(
    session_dir: Path,
    *,
    png: Path,
    vql: Path,
) -> dict[str, str]:
    """Copy fresh capture + sidecars into session observe/ and pin env paths."""
    dest_png, dest_vql = session_observe_paths(session_dir)
    if png.resolve() != dest_png.resolve() and png.is_file():
        dest_png.write_bytes(png.read_bytes())
    if vql.resolve() != dest_vql.resolve() and vql.is_file():
        dest_vql.write_text(vql.read_text(encoding="utf-8"), encoding="utf-8")

    ctx = png.with_suffix(png.suffix + ".context.json")
    dest_ctx = dest_png.with_suffix(dest_png.suffix + ".context.json")
    if ctx.is_file() and ctx.resolve() != dest_ctx.resolve():
        dest_ctx.write_text(ctx.read_text(encoding="utf-8"), encoding="utf-8")

    imgl = Path(str(vql).replace(".png.vql.json", ".png.vql.imgl.json"))
    dest_imgl = Path(str(dest_vql).replace(".png.vql.json", ".png.vql.imgl.json"))
    if imgl.is_file() and imgl.resolve() != dest_imgl.resolve():
        dest_imgl.write_text(imgl.read_text(encoding="utf-8"), encoding="utf-8")

    os.environ["KORU_VDISPLAY_PHOTO_PATH"] = str(dest_png.resolve())
    os.environ["KORU_VDISPLAY_VQL_PATH"] = str(dest_vql.resolve())
    return {"png": str(dest_png), "vql": str(dest_vql)}


__all__ = [
    "active_session_dir",
    "append_session_index",
    "begin_autonomy_session",
    "copy_observe_artifacts_to_session",
    "metadata_root",
    "persist_autonomy_phase",
    "session_observe_paths",
    "vql_max_age_seconds",
    "vql_sidecar_is_stale",
    "append_session_jsonl",
    "find_latest_koru_session",
]
