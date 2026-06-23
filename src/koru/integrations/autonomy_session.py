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
    _create_session_dirs(session_dir)
    manifest = _session_manifest(ide=ide, source=source, started_at=now)
    (session_dir / "session.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    png, vql = session_observe_paths(session_dir)
    _pin_session_env(session_dir=session_dir, slug=slug, png=png, vql=vql)
    return session_dir


def _create_session_dirs(session_dir: Path) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("observe", "decide", "act", "verify"):
        (session_dir / sub).mkdir(exist_ok=True)


def _session_manifest(*, ide: str, source: str, started_at: datetime) -> dict[str, Any]:
    return {
        "kind": "koru-autonomy-session",
        "started_at": started_at.isoformat(),
        "ide": ide,
        "source": source,
        "observe_dir": "observe",
        "decide_dir": "decide",
        "act_dir": "act",
        "verify_dir": "verify",
        "vql_max_age_s": vql_max_age_seconds(),
    }


def _pin_session_env(*, session_dir: Path, slug: str, png: Path, vql: Path) -> None:
    resolved = str(session_dir.resolve())
    os.environ["KORU_AUTONOMY_SESSION_DIR"] = resolved
    os.environ["VDISPLAY_SESSION_DIR"] = resolved
    os.environ.setdefault("VDISPLAY_SESSION", "1")
    os.environ.setdefault("VDISPLAY_SESSION_ID", f"koru-{slug}")
    os.environ["KORU_VDISPLAY_PHOTO_PATH"] = str(png.resolve())
    os.environ["KORU_VDISPLAY_VQL_PATH"] = str(vql.resolve())


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
    bases: list[Path] = []
    if root is not None:
        bases.append(root)
    else:
        env_root = os.environ.get("VDISPLAY_METADATA_DIR", "").strip()
        if env_root:
            bases.append(Path(env_root).expanduser())
        proj = os.environ.get("KORU_PROJECT_ROOT", "").strip()
        if proj:
            bases.append(Path(proj).expanduser() / ".vdisplay")
        cwd_root = Path.cwd() / ".vdisplay"
        if cwd_root not in bases:
            bases.append(cwd_root)
        if not bases:
            bases.append(metadata_root())
    slug = (ide or "jetbrains").strip().lower().replace(" ", "-")[:32]
    pattern = f"*__koru-{slug}"
    candidates: list[Path] = []
    seen: set[Path] = set()
    for base in bases:
        if not base.is_dir():
            continue
        for child in base.iterdir():
            if not child.is_dir():
                continue
            for session in child.glob(pattern):
                if not session.is_dir():
                    continue
                resolved = session.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                candidates.append(resolved)
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
        return True, _missing_vql_info(vql_path)

    vql_mt = vql_path.stat().st_mtime
    info = _base_vql_stale_info(vql_path=vql_path, vql_mtime=vql_mt, now=now, max_age=max_age, reasons=reasons)

    if capture_validation is None:
        capture_validation = _vql_load_capture_validation(vql_path)

    _append_vql_age_reason(reasons=reasons, age_s=now - vql_mt, max_age=max_age)
    _append_png_staleness(
        info=info,
        reasons=reasons,
        png_path=png_path,
        vql_mtime=vql_mt,
        now=now,
        max_age=max_age,
    )
    _append_layer_count_reason(reasons=reasons, layer_count=layer_count)
    _append_capture_validation_reasons(
        info=info,
        reasons=reasons,
        window_mismatch=window_mismatch,
        capture_validation=capture_validation,
    )

    info["stale"] = bool(reasons)
    info["reasons"] = reasons
    return bool(reasons), info


def _missing_vql_info(vql_path: Path) -> dict[str, Any]:
    return {"stale": True, "reasons": ["missing_vql"], "vql_path": str(vql_path)}


def _base_vql_stale_info(
    *,
    vql_path: Path,
    vql_mtime: float,
    now: float,
    max_age: float,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "stale": False,
        "reasons": reasons,
        "vql_path": str(vql_path.resolve()),
        "vql_mtime": vql_mtime,
        "age_s": round(now - vql_mtime, 2),
        "max_age_s": max_age,
    }


def _append_vql_age_reason(*, reasons: list[str], age_s: float, max_age: float) -> None:
    if max_age > 0 and age_s > max_age:
        reasons.append(f"vql_age_s>{max_age}")


def _append_png_staleness(
    *,
    info: dict[str, Any],
    reasons: list[str],
    png_path: Path | None,
    vql_mtime: float,
    now: float,
    max_age: float,
) -> None:
    if png_path is None:
        return
    if not png_path.is_file():
        reasons.append("missing_png")
        return
    png_mtime = png_path.stat().st_mtime
    info["png_mtime"] = png_mtime
    info["png_path"] = str(png_path.resolve())
    _append_png_age_reason(reasons=reasons, png_mtime=png_mtime, now=now, max_age=max_age)
    _append_sidecar_order_reason(reasons=reasons, png_mtime=png_mtime, vql_mtime=vql_mtime)


def _append_png_age_reason(
    *,
    reasons: list[str],
    png_mtime: float,
    now: float,
    max_age: float,
) -> None:
    if max_age > 0 and (now - png_mtime) > max_age:
        reasons.append(f"png_age_s>{max_age}")


def _append_sidecar_order_reason(
    *,
    reasons: list[str],
    png_mtime: float,
    vql_mtime: float,
) -> None:
    # Depending on the capture backend, the VQL sidecar can be flushed before
    # the final PNG write. Treat small deltas as one capture transaction.
    try:
        write_grace_s = max(2.0, float(os.environ.get("KORU_VDISPLAY_SIDECAR_WRITE_GRACE_S", "30") or "30"))
    except ValueError:
        write_grace_s = 30.0
    if vql_mtime + write_grace_s < png_mtime:
        reasons.append("vql_sidecar_older_than_png")
    elif png_mtime > vql_mtime + 600.0:
        reasons.append("png_newer_than_vql_by_600s")


def _append_layer_count_reason(*, reasons: list[str], layer_count: int | None) -> None:
    if layer_count is not None and layer_count == 0:
        reasons.append("empty_vql_layers")


def _append_capture_validation_reasons(
    *,
    info: dict[str, Any],
    reasons: list[str],
    window_mismatch: dict[str, Any] | None,
    capture_validation: dict[str, Any] | None,
) -> None:
    if window_mismatch is not None:
        reasons.append("ide_window_mismatch")
        info["ide_window_warning"] = window_mismatch
        return
    if not isinstance(capture_validation, dict):
        return
    info["capture_validation"] = capture_validation
    expected = str(capture_validation.get("expected_ide") or "").strip()
    if expected and capture_validation.get("capture_confirmed") is False:
        reasons.append("capture_validation_failed")
        _append_unique_reasons(reasons, capture_validation.get("reasons") or [])


def _append_unique_reasons(reasons: list[str], items: Any) -> None:
    for item in items:
        if item not in reasons:
            reasons.append(str(item))


def copy_observe_artifacts_to_session(
    session_dir: Path,
    *,
    png: Path,
    vql: Path,
) -> dict[str, str]:
    """Copy fresh capture + sidecars into session observe/ and pin env paths."""
    dest_png, dest_vql = session_observe_paths(session_dir)
    _copy_binary_if_needed(src=png, dest=dest_png)
    _copy_text_if_needed(src=vql, dest=dest_vql)
    _copy_text_if_needed(
        src=png.with_suffix(png.suffix + ".context.json"),
        dest=dest_png.with_suffix(dest_png.suffix + ".context.json"),
    )
    _copy_text_if_needed(src=_imgl_sidecar_path(vql), dest=_imgl_sidecar_path(dest_vql))
    _pin_observe_env(dest_png=dest_png, dest_vql=dest_vql)
    return {"png": str(dest_png), "vql": str(dest_vql)}


def _same_resolved_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def _copy_binary_if_needed(*, src: Path, dest: Path) -> None:
    if src.is_file() and not _same_resolved_path(src, dest):
        dest.write_bytes(src.read_bytes())


def _copy_text_if_needed(*, src: Path, dest: Path) -> None:
    if src.is_file() and not _same_resolved_path(src, dest):
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _imgl_sidecar_path(vql_path: Path) -> Path:
    return Path(str(vql_path).replace(".png.vql.json", ".png.vql.imgl.json"))


def _pin_observe_env(*, dest_png: Path, dest_vql: Path) -> None:
    os.environ["KORU_VDISPLAY_PHOTO_PATH"] = str(dest_png.resolve())
    os.environ["KORU_VDISPLAY_VQL_PATH"] = str(dest_vql.resolve())


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
