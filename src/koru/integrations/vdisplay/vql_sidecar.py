"""VQL sidecar observation, PNG resolution and sidecar refresh extracted
from ``vdisplay_client``.

Moved verbatim from the historical ``vdisplay_client`` monolith; the
facade re-exports every name, so ``from koru.integrations.vdisplay_client
import X`` keeps working. References that were ``vdisplay_client`` module
globals resolve through the facade at call time (``_vdc()``) so
``monkeypatch.setattr(vdisplay_client, ...)`` keeps steering the pipeline.
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Any


def _vdc():
    """The vdisplay_client facade (imported lazily: it imports this module)."""
    import koru.integrations.vdisplay_client as m

    return m


def _photo_vql_metadata_root() -> Path:
    from pathlib import Path

    return Path(os.environ.get("VDISPLAY_METADATA_DIR", ".vdisplay")).expanduser()


def _capture_confirmed_from_meta(*, ide: str, meta: dict | None) -> bool:
    """Single source of truth: observe sidecar only (never map file mtime)."""
    meta = meta or {}
    if _vdc()._photo_vql_system_overlay_warning(meta=meta):
        return False
    cv = _vdc()._capture_validation_from_meta(meta)
    if isinstance(cv, dict) and cv.get("capture_confirmed") is not None:
        return bool(cv.get("capture_confirmed"))
    if _vdc()._photo_vql_ide_window_warning(ide=ide, meta=meta):
        return False
    titles = _vdc()._window_titles_from_vql_meta(meta)
    return bool(titles)


def _capture_provenance(
    *,
    ide: str,
    png_path: str | None = None,
    vql_path: str | None = None,
    meta: dict | None = None,
) -> dict[str, Any]:
    """Timestamps + window titles from the observe capture (audit / drive_reply)."""
    prov: dict[str, Any] = {"ide": ide}
    for key, path in (("png", png_path), ("vql", vql_path)):
        if path and os.path.isfile(path):
            try:
                st = os.stat(path)
                prov[f"{key}_path"] = path
                prov[f"{key}_mtime"] = st.st_mtime
                prov[f"{key}_mtime_iso"] = datetime.datetime.fromtimestamp(st.st_mtime).isoformat()
            except OSError:
                pass
    meta = meta or {}
    titles = _vdc()._window_titles_from_vql_meta(meta)
    if titles:
        prov["window_titles"] = titles
        prov["capture_title"] = titles[0]
    warn = _vdc()._photo_vql_ide_window_warning(ide=ide, meta=meta) if meta else None
    prov["capture_confirmed"] = _vdc()._capture_confirmed_from_meta(ide=ide, meta=meta)
    if warn:
        prov["ide_window_warning"] = warn
    return prov


def _photo_vql_capture_validation_failed_warning(
    cv: dict[str, Any], *, ide: str, meta: dict
) -> dict[str, Any]:
    return _vdc().photo_vql_capture_validation_failed_warning(
        cv, ide=ide, meta=meta, window_titles=_vdc()._window_titles_from_vql_meta
    )


def _photo_vql_expected_title_tokens(canon: str) -> tuple[str, ...]:
    return _vdc().photo_vql_expected_title_tokens(canon, ide_hints=_vdc()._ide_hints)


def _photo_vql_title_mismatch_warning(
    canon: str, tokens: tuple[str, ...], titles: list[str]
) -> dict[str, Any] | None:
    return _vdc().photo_vql_title_mismatch_warning(canon, tokens, titles)


def _photo_vql_ide_window_warning(*, ide: str, meta: dict) -> dict[str, Any] | None:
    return _vdc().photo_vql_ide_window_warning(
        ide=ide,
        meta=meta,
        window_titles=_vdc()._window_titles_from_vql_meta,
        ide_hints=_vdc()._ide_hints,
    )


def _photo_vql_ide_capture_mismatch(*, ide: str) -> dict[str, Any] | None:
    """Return warning dict when the current photo-VQL sidecar does not match the requested IDE."""
    meta: dict[str, Any] | None = None
    session = _vdc()._autonomy_session.active_session_dir()
    if session is not None:
        _png, vql = _vdc()._autonomy_session.session_observe_paths(session)
        if vql.is_file():
            meta = _vdc().load_vql_metadata(str(vql), allow_stale=True)
    if meta is None or not (meta.get("ui_elements") or meta.get("layers")):
        try:
            meta = _vdc().load_vql_metadata(allow_stale=True)
        except Exception:
            return None
    if meta.get("error"):
        return None
    return _vdc()._photo_vql_ide_window_warning(ide=ide, meta=meta)


def _observe_vql_sidecar_path(*, source: str | None = None) -> str | None:
    """Resolve observe-phase VQL sidecar (never map/calibration paths)."""
    from pathlib import Path

    session = _vdc()._autonomy_session.active_session_dir()
    if session is not None:
        _png, vql = _vdc()._autonomy_session.session_observe_paths(session)
        if vql.is_file():
            return str(vql)
    explicit = os.environ.get("KORU_VDISPLAY_VQL_PATH", "").strip()
    if explicit and explicit.endswith(".vql.json") and os.path.isfile(explicit):
        return explicit
    png = _vdc()._resolve_photo_png_path_from_vql(source=source)
    if png and os.path.isfile(png):
        sidecar = str(Path(png).with_suffix(Path(png).suffix + ".vql.json"))
        if os.path.isfile(sidecar):
            return sidecar
    return None


def _annotate_png_artifact_state(out: dict[str, Any]) -> dict[str, Any]:
    raw = str(out.get("png") or "").strip()
    if not raw:
        out.setdefault("png_exists", False)
        return out
    # A failed capture/refresh must never inherit a file already sitting at the
    # requested path — that stale screenshot (e.g. /tmp/capture.png from a prior
    # session) would false-positive as a fresh confirmation and let koru actuate
    # on the wrong screen. Distrust the path whenever the step reported failure.
    capture_failed = bool(out.get("ok") is False or out.get("error") or out.get("returncode"))
    path = Path(raw).expanduser()
    exists = path.is_file()
    if capture_failed:
        out["png_exists"] = False
        out.setdefault("requested_png_path", raw)
        out["png"] = None
        return out
    out["png_exists"] = exists
    if exists:
        out["png"] = str(path.resolve())
        return out
    out.setdefault("requested_png_path", raw)
    return out


def _photo_png_from_vql_sidecar_path(cand_vql: str) -> str | None:
    """Derive the PNG path from a VQL sidecar filename (with metadata-root fallback)."""
    from pathlib import Path

    if cand_vql.endswith(".png.vql.json"):
        png = cand_vql[: -len(".vql.json")]
    elif cand_vql.endswith(".vql.json"):
        png = cand_vql[: -len(".vql.json")]
    else:
        png = cand_vql
    if os.path.isfile(png):
        return png
    rooted = _vdc()._photo_vql_metadata_root() / Path(png).name
    if rooted.is_file():
        return str(rooted)
    return None


def _photo_png_from_vql_metadata(cand_vql: str) -> str | None:
    """Resolve the PNG path from VQL metadata data_locations / scene URL."""
    try:
        meta = _vdc().load_vql_metadata(cand_vql or None)
        dl = meta.get("data_locations") if isinstance(meta.get("data_locations"), dict) else {}
        png_from_meta = (dl or {}).get("png") if isinstance(dl, dict) else None
        if png_from_meta and os.path.isfile(png_from_meta):
            return png_from_meta
        scene = meta.get("scene") if isinstance(meta.get("scene"), dict) else {}
        url = str((scene or {}).get("url") or "")
        if url.startswith("file://") and os.path.isfile(url[7:]):
            return url[7:]
    except Exception:
        pass
    return None


def _resolve_photo_png_path_from_vql(
    *,
    vql_path: str | None = None,
    source: str | None = None,
) -> str | None:
    """Resolve the screenshot PNG paired with a photo-VQL sidecar (for LLM vision)."""
    explicit = os.environ.get("KORU_VDISPLAY_PHOTO_PATH", "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit

    cand_vql = (vql_path or os.environ.get("KORU_VDISPLAY_VQL_PATH", "")).strip()
    if cand_vql:
        png = _vdc()._photo_png_from_vql_sidecar_path(cand_vql)
        if png:
            return png

    png_from_meta = _vdc()._photo_png_from_vql_metadata(cand_vql)
    if png_from_meta:
        return png_from_meta

    src = source or _vdc()._vdisplay_source()
    png_path = _vdc()._resolve_photo_png_path(src)
    return str(png_path) if png_path.is_file() else None


def _resolve_photo_png_path(source: str) -> Path:
    import glob
    from pathlib import Path

    session = _vdc()._autonomy_session.active_session_dir()
    if session is not None:
        png, _vql = _vdc()._autonomy_session.session_observe_paths(session)
        return png

    explicit = os.environ.get("KORU_VDISPLAY_PHOTO_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    root = _vdc()._photo_vql_metadata_root()
    slug_raw = source.strip().lower().replace("/", "-")
    slug_compact = slug_raw.replace("-", "")
    patterns = [
        f"koru-cont-{slug_raw}.png",
        f"koru-cont-{slug_compact}.png",
        f"koru-cont-{slug_raw}-*.png",
        f"koru-cont-{slug_compact}-*.png",
    ]
    for pattern in patterns:
        matches = [p for p in glob.glob(str(root / pattern)) if os.path.isfile(p)]
        if matches:
            matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return Path(matches[0])
    return root / f"koru-cont-{slug_compact}.png"


def _photo_vql_refresh_mode() -> str:
    return os.environ.get("KORU_VDISPLAY_PHOTO_VQL_REFRESH", "auto").strip().lower()


def photo_vql_sidecar_needs_refresh(*, source: str | None = None, ide: str = "auto") -> bool:
    """True when autonomy should capture a fresh screenshot before photo-VQL drive."""
    if _vdc()._surface_only_fallback_active():
        return False
    mode = _vdc()._photo_vql_refresh_mode()
    if mode in {"0", "false", "no", "off"}:
        return False
    if mode in {"1", "true", "yes", "on", "always"}:
        return True
    src = source or _vdc()._vdisplay_source_for_ide(ide)
    png = _vdc()._resolve_photo_png_path(src)
    vql = png.with_suffix(png.suffix + ".vql.json")
    if not png.is_file() or not vql.is_file():
        return True
    meta = _vdc().load_vql_metadata(str(vql), allow_stale=True)
    layers = meta.get("ui_elements") or meta.get("layers") or []
    warn = _vdc()._photo_vql_ide_window_warning(ide=ide, meta=meta)
    stale, _info = _vdc()._autonomy_session.vql_sidecar_is_stale(
        vql,
        png,
        ide=ide,
        layer_count=len(layers),
        window_mismatch=warn,
    )
    return stale


def _photo_vql_refresh_dry_run_out(
    src: str, png: Path, vql: Path, session: Path | None
) -> dict[str, Any]:
    """Dry-run result for refresh_photo_vql_sidecar (no capture performed)."""
    os.environ["KORU_VDISPLAY_VQL_PATH"] = str(vql)
    out = {
        "ok": True,
        "dry_run": True,
        "source": src,
        "png": str(png),
        "vql": str(vql),
        "elements": 0,
    }
    if session is not None:
        out["session_dir"] = str(session)
    return out


def _photo_vql_refresh_screenshot(src: str, png: Path, ide: str) -> dict[str, Any] | None:
    """Run the vdisplay screenshot CLI; return an error dict on failure, None on success."""
    import subprocess

    cmd = [
        _vdc()._vdisplay_cli_path(),
        "screenshot",
        "-o",
        str(png),
        "--source",
        src,
    ]
    env = _vdc()._vdisplay_subprocess_env(ide=ide)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False, env=env)
    except Exception as exc:
        error = str(exc)
        return _vdc()._annotate_png_artifact_state({
            "ok": False,
            "error": error,
            "hint": _vdc()._vdisplay_capture_failure_hint(error),
            "source": src,
            "png": str(png),
        })

    if proc.returncode != 0:
        error = (proc.stderr or proc.stdout or "screenshot failed").strip()
        return _vdc()._annotate_png_artifact_state({
            "ok": False,
            "error": error,
            "hint": _vdc()._vdisplay_capture_failure_hint(error),
            "source": src,
            "png": str(png),
            "returncode": proc.returncode,
        })
    return None


def _photo_vql_reload_sidecar_meta(vql: Path) -> dict[str, Any]:
    """Fresh (meta, elements, main_layers) context loaded from the VQL sidecar."""
    meta = _vdc().load_vql_metadata(str(vql), allow_stale=True)
    return {
        "meta": meta,
        "elements": meta.get("ui_elements") or meta.get("layers") or [],
        "main_layers": _vdc()._main_vql_layer_count(vql),
    }


def _photo_vql_observe_when_empty(
    *,
    png: Path,
    vql: Path,
    src: str,
    ide: str,
    session: Path | None,
    meta: dict[str, Any],
    elements: list,
    main_layers: int,
) -> dict[str, Any]:
    """Re-observe an empty sidecar; returns loaded context with an optional early_out."""
    loaded = {"meta": meta, "elements": elements, "main_layers": main_layers}
    observe_subprocess = _vdc()._refresh_vql_sidecar_via_vdisplay_observe(
        png=png,
        vql=vql,
        source=src,
        ide=ide,
    )
    if observe_subprocess.get("ok"):
        loaded = _vdc()._photo_vql_reload_sidecar_meta(vql)
    try:
        if loaded["main_layers"] == 0:
            _vdc()._ensure_real_imgl_on_path()
            from vdisplay.integrations.pipeline import observe_screen

            observe_screen(
                image_path=png,
                capture_meta={"path": str(png.resolve()), "source": src},
                write_sidecar=True,
            )
            loaded = _vdc()._photo_vql_reload_sidecar_meta(vql)
    except Exception as exc:
        out = {
            "ok": True,
            "source": src,
            "png": str(png.resolve()),
            "vql": str(vql.resolve()) if vql.is_file() else str(vql),
            "elements": len(loaded["elements"]),
            "main_vql_layers": loaded["main_layers"],
            "observe_subprocess": observe_subprocess,
            "observe_fallback_error": str(exc),
        }
        if session is not None:
            out["session_dir"] = str(session)
        return {**loaded, "observe_subprocess": observe_subprocess, "early_out": out}
    return {**loaded, "observe_subprocess": observe_subprocess, "early_out": None}


def _photo_vql_refresh_annotate_observe(
    out: dict[str, Any], main_layers: int, observe_subprocess: dict[str, Any] | None
) -> None:
    """Attach the observe-subprocess summary to the refresh result."""
    if main_layers > 0 and observe_subprocess is not None and observe_subprocess.get("ok"):
        out["observe_subprocess"] = {
            "ok": True,
            "method": observe_subprocess.get("method"),
            "returncode": observe_subprocess.get("returncode"),
        }
    elif main_layers == 0 and observe_subprocess is not None:
        out["observe_subprocess"] = observe_subprocess


def _photo_vql_refresh_finalize_out(
    out: dict[str, Any],
    *,
    ide: str,
    meta: dict[str, Any],
    png: Path,
    vql: Path,
    session: Path | None,
) -> dict[str, Any]:
    """Warnings, provenance and session artifact copies for the refresh result."""
    warn = _vdc()._photo_vql_ide_window_warning(ide=ide, meta=meta)
    if warn:
        out["ide_window_warning"] = warn
    if meta.get("capture_validation"):
        out["capture_validation"] = meta["capture_validation"]
    out["capture_provenance"] = _vdc()._capture_provenance(
        ide=ide, png_path=str(png), vql_path=str(vql), meta=meta
    )
    out["capture_confirmed"] = out["capture_provenance"].get("capture_confirmed")
    if session is not None:
        out["session_dir"] = str(session)
        if png.is_file() and vql.is_file():
            copied = _vdc()._autonomy_session.copy_observe_artifacts_to_session(
                session,
                png=png,
                vql=vql,
            )
            out["observe_session_paths"] = copied
            out["png"] = copied["png"]
            out["vql"] = copied["vql"]
    return out


def _photo_vql_refresh_context(*, source: str | None, ide: str) -> dict[str, Any]:
    """Resolve and pin the source/session/png/vql context for a sidecar refresh."""
    src = source or _vdc()._vdisplay_source_for_ide(ide)
    os.environ["KORU_VDISPLAY_SOURCE"] = src
    session = _vdc()._autonomy_session.active_session_dir()
    png = _vdc()._resolve_photo_png_path(src)
    png.parent.mkdir(parents=True, exist_ok=True)
    return {
        "src": src,
        "ide": ide,
        "session": session,
        "png": png,
        "vql": png.with_suffix(png.suffix + ".vql.json"),
    }


def _photo_vql_refresh_observe_if_empty(ctx: dict[str, Any]) -> dict[str, Any] | None:
    """Re-observe an empty sidecar into the context; returns an early-out result or None."""
    if ctx["main_layers"] > 0 or not ctx["png"].is_file():
        return None
    observed = _vdc()._photo_vql_observe_when_empty(
        png=ctx["png"],
        vql=ctx["vql"],
        src=ctx["src"],
        ide=ctx["ide"],
        session=ctx["session"],
        meta=ctx["meta"],
        elements=ctx["elements"],
        main_layers=ctx["main_layers"],
    )
    early_out = observed["early_out"]
    if early_out is not None:
        return early_out
    ctx.update(
        meta=observed["meta"],
        elements=observed["elements"],
        main_layers=observed["main_layers"],
        observe_subprocess=observed["observe_subprocess"],
    )
    return None


def _photo_vql_refresh_capture(ctx: dict[str, Any]) -> dict[str, Any] | None:
    """Dry-run gate + screenshot + sidecar reload; returns an early-out result or None."""
    if _vdc()._dry_run():
        return _vdc()._photo_vql_refresh_dry_run_out(ctx["src"], ctx["png"], ctx["vql"], ctx["session"])
    capture_error = _vdc()._photo_vql_refresh_screenshot(ctx["src"], ctx["png"], ctx["ide"])
    if capture_error is not None:
        return capture_error
    os.environ["KORU_VDISPLAY_VQL_PATH"] = str(ctx["vql"])
    loaded = _vdc()._photo_vql_reload_sidecar_meta(ctx["vql"])
    loaded["observe_subprocess"] = None
    ctx.update(loaded)
    return _vdc()._photo_vql_refresh_observe_if_empty(ctx)


def _photo_vql_refresh_stale_out(ctx: dict[str, Any]) -> dict[str, Any]:
    """Staleness + result fields + observe annotation for the refresh result."""
    stale, freshness = _vdc()._autonomy_session.vql_sidecar_is_stale(
        ctx["vql"],
        ctx["png"],
        ide=ctx["ide"],
        layer_count=len(ctx["elements"]),
        window_mismatch=_vdc()._photo_vql_ide_window_warning(ide=ctx["ide"], meta=ctx["meta"]),
        capture_validation=ctx["meta"].get("capture_validation"),
    )
    out: dict[str, Any] = {
        "ok": True,
        "source": ctx["src"],
        "png": str(ctx["png"].resolve()) if ctx["png"].is_file() else str(ctx["png"]),
        "vql": str(ctx["vql"].resolve()) if ctx["vql"].is_file() else str(ctx["vql"]),
        "elements": len(ctx["elements"]),
        "main_vql_layers": ctx["main_layers"],
        "vql_source": ctx["meta"].get("_source"),
        "freshness": freshness,
        "sidecar_stale": stale,
    }
    _vdc()._photo_vql_refresh_annotate_observe(out, ctx["main_layers"], ctx["observe_subprocess"])
    return out


def refresh_photo_vql_sidecar(*, source: str | None = None, ide: str = "auto") -> dict[str, Any]:
    """Capture fresh screenshot + VQL sidecar for photo-VQL drive (observe via vdisplay CLI/agent)."""
    ctx = _vdc()._photo_vql_refresh_context(source=source, ide=ide)
    early_out = _vdc()._photo_vql_refresh_capture(ctx)
    if early_out is not None:
        return early_out
    out = _vdc()._photo_vql_refresh_stale_out(ctx)
    return _vdc()._photo_vql_refresh_finalize_out(
        out, ide=ctx["ide"], meta=ctx["meta"], png=ctx["png"], vql=ctx["vql"], session=ctx["session"]
    )


def _vdisplay_capture_failure_hint(error: str) -> str | None:
    text = str(error or "").lower()
    hints: list[str] = []
    if "python3-dbus" in text or "no module named 'dbus'" in text:
        hints.append("Install/enable dbus bindings for the Python used by vdisplay-agent (python3-dbus / dbus-python).")
    if "screen recording" in text or "portal screenshot denied" in text:
        hints.append("GNOME Wayland: Settings -> Privacy -> Screen Recording -> allow the terminal/IDE running vdisplay-agent.")  # noqa: E501
    if "pipewire" in text or "gstreamer" in text or "timed out after" in text:
        hints.append("ScreenCast frame capture timed out; prefer `koru autopilot vdisplay-up --ide jetbrains`, then in Chrome/Chromium click Share screen and keep the browser bridge tab open. Keeper fallback: `vdisplay agent screencast start --force` and probe with `vdisplay agent screencast probe --via-agent --source <monitor>`.")  # noqa: E501
    if "list index out of range" in text:
        hints.append("vdisplay-agent capture route raised an internal stream-index error; prefer browser bridge via `koru autopilot vdisplay-up --ide jetbrains`; if using keeper, restart `vdisplay-agent serve` and `vdisplay agent screencast start --force`, then probe the monitor via agent.")  # noqa: E501
    if "persistent screencast" in text or "vdisplay-agent serve" in text or "gnome-screenshot" in text:
        hints.append("Use browser bridge first: `koru autopilot vdisplay-up --ide jetbrains`; in Chrome/Chromium choose the IDE monitor and keep the tab open. Keeper fallback: `vdisplay-agent serve`, then `vdisplay agent screencast start`.")  # noqa: E501
    return " | ".join(dict.fromkeys(hints)) or None


def _refresh_vql_sidecar_via_vdisplay_observe(
    *,
    png: Path,
    vql: Path,
    source: str,
    ide: str = "auto",
) -> dict[str, Any]:
    """Rebuild VQL sidecars through a Python env with vdisplay + imgl.

    Koru's venv intentionally stays small and may not include Pillow/tesseract
    dependencies required by semcod/imgl.  This helper observes the existing
    PNG without taking another screenshot, so a good capture is not overwritten
    by a later blank frame.
    """
    import subprocess

    env = _vdc()._vdisplay_subprocess_env(ide=ide)
    env["VDISPLAY_OBSERVE"] = "1"
    env["VDISPLAY_OBSERVE_VQL"] = "1"
    env["VDISPLAY_OBSERVE_SIDECAR"] = "1"
    env["VDISPLAY_OBSERVE_CACHE"] = "0"
    env["VDISPLAY_IMGL"] = "1"
    attempts: list[dict[str, Any]] = []
    code = """
from __future__ import annotations
import json
import sys
from pathlib import Path

png = Path(sys.argv[1])
vql = Path(sys.argv[2])
source = sys.argv[3]

from vdisplay.integrations.pipeline import observe_screen

ctx = observe_screen(
    image_path=png,
    capture_meta={"path": str(png.resolve()), "source": source},
    write_sidecar=True,
    vql_path=vql,
)
program = (ctx.vql or {}).get("program") or {}
render = (program.get("metadata") or {}).get("render_intent") or {}
print(json.dumps({
    "ok": True,
    "image": str(png.resolve()),
    "vql": str(vql.resolve()),
    "imgl_ok": ctx.imgl.get("ok"),
    "imgl_error": ctx.imgl.get("error"),
    "program_layers": len(program.get("layers") or []),
    "render_layers": len(render.get("layers") or []),
}, ensure_ascii=False))
"""
    for python in _vdc()._vdisplay_observe_python_candidates():
        cmd = [
            python,
            "-c",
            code,
            str(png),
            str(vql),
            source,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False, env=env)
        except Exception as exc:
            attempts.append(
                {
                    "python": python,
                    "ok": False,
                    "error": str(exc),
                    "method": "vdisplay_observe_python",
                }
            )
            continue
        layer_count = _vdc()._main_vql_layer_count(vql)
        attempt: dict[str, Any] = {
            "python": python,
            "ok": proc.returncode == 0 and layer_count > 0,
            "method": "vdisplay_observe_python",
            "returncode": proc.returncode,
            "main_vql_layers": layer_count,
        }
        if proc.stdout.strip():
            attempt["stdout"] = proc.stdout.strip()
        if proc.stderr.strip():
            attempt["stderr"] = proc.stderr.strip()
        if proc.returncode != 0:
            attempt["error"] = (proc.stderr or proc.stdout or "vdisplay observe failed").strip()
        elif layer_count <= 0:
            attempt["error"] = "vdisplay observe produced empty VQL layers"
        attempts.append(attempt)
        if attempt["ok"]:
            return {**attempt, "attempts": attempts}
    error = attempts[-1].get("error") if attempts else "vdisplay observe failed"
    return {
        "ok": False,
        "method": "vdisplay_observe_python",
        "error": error,
        "attempts": attempts,
    }
