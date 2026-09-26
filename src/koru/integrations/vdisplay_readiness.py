"""Runtime discovery, agent probing, fallback policies and readiness for vdisplay.

Extracted from ``koru.integrations.vdisplay_client`` to decompose the God Module.
Re-exported from ``vdisplay_client`` for 100% backward compatibility.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable


def _real_vdisplay_src() -> str | None:
    candidates: list[str] = []
    explicit = os.environ.get("VDISPLAY_SRC", "").strip()
    if explicit:
        candidates.append(explicit)
    candidates.append(str(Path.home() / "github/wronai/vdisplay/src"))
    candidates.append(str(Path.home() / "github/wronai/vdisplay"))
    for raw in candidates:
        root = Path(raw).expanduser()
        src_root = root / "src" if (root / "src" / "vdisplay").is_dir() else root
        if (src_root / "vdisplay" / "ide_prompt.py").is_file():
            return str(src_root)
    return None


def _ensure_real_vdisplay_on_path() -> None:
    root = _real_vdisplay_src()
    if not root:
        return
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    pkg = sys.modules.get("vdisplay")
    pkg_path = str(Path(root) / "vdisplay")
    paths = getattr(pkg, "__path__", None)
    if paths is not None and pkg_path not in list(paths):
        try:
            paths.insert(0, pkg_path)
        except AttributeError:
            paths.append(pkg_path)


_VDISPLAY_DIRECT: bool = False
_VDISPLAY_IMPORT_ERROR: str | None = None
_vdisplay_control: Any = None


def _load_vdisplay_control() -> bool:
    """Lazy load to avoid top-level crashes from vdisplay submodules and make autonomy robust."""
    global _VDISPLAY_DIRECT, _VDISPLAY_IMPORT_ERROR, _vdisplay_control
    if _vdisplay_control is not None or _VDISPLAY_DIRECT:
        return _VDISPLAY_DIRECT
    try:
        from vdisplay.application.services import control as control_mod

        _vdisplay_control = control_mod
        _VDISPLAY_DIRECT = True
        _VDISPLAY_IMPORT_ERROR = None
        return True
    except Exception as exc:
        _VDISPLAY_DIRECT = False
        _VDISPLAY_IMPORT_ERROR = str(exc)
        return False


def _init_vdisplay_direct() -> None:
    global _VDISPLAY_DIRECT, _VDISPLAY_IMPORT_ERROR, _vdisplay_control
    _ensure_real_vdisplay_on_path()
    try:
        from vdisplay.application.services import control as control_mod

        _vdisplay_control = control_mod
        _VDISPLAY_DIRECT = True
    except Exception as exc:
        _VDISPLAY_IMPORT_ERROR = str(exc)
        _vdisplay_control = None


_init_vdisplay_direct()


def _canonical_ide(ide: str) -> str:
    try:
        from koruide.ide import canonical_autopilot_ide_id

        return canonical_autopilot_ide_id(ide) or ide.strip().lower()
    except Exception:
        return ide.strip().lower()


def _agent_url() -> str | None:
    explicit = os.environ.get("KORU_VDISPLAY_AGENT_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    try:
        from koru.integrations.vdisplay_agent_bootstrap import (
            apply_vdisplay_agent_env,
            resolve_vdisplay_agent_url,
        )

        applied = apply_vdisplay_agent_env()
        url = applied.get("agent_url") or resolve_vdisplay_agent_url()
        if url:
            return url.rstrip("/")
        from vdisplay.agent_config import resolve_agent_url

        return resolve_agent_url(allow_auto=True)
    except ImportError:
        try:
            from koru.integrations.vdisplay_agent_bootstrap import resolve_vdisplay_agent_url

            url = resolve_vdisplay_agent_url()
            return url.rstrip("/") if url else None
        except ImportError:
            return None


def _probe_agent(url: str) -> bool:
    try:
        from koru.integrations.vdisplay_agent_bootstrap import probe_vdisplay_agent

        return probe_vdisplay_agent(url.rstrip("/"))
    except ImportError:
        pass
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/health", timeout=0.5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def _reload_vdisplay_direct() -> bool:
    return _load_vdisplay_control()


def _ensure_vdisplay_runtime(
    *,
    direct: bool | None = None,
    reload_fn: Callable[[], bool] | None = None,
) -> bool:
    is_direct = _VDISPLAY_DIRECT if direct is None else direct
    if is_direct:
        return True
    from koru.deps_autorepair import ensure_vdisplay_runtime

    if not ensure_vdisplay_runtime(label="koru drive"):
        return False
    rl_fn = _reload_vdisplay_direct if reload_fn is None else reload_fn
    return rl_fn()


def vdisplay_available(
    *,
    direct: bool | None = None,
    load_control: Callable[[], bool] | None = None,
    ensure_runtime: Callable[[], bool] | None = None,
    agent_url_fn: Callable[[], str | None] | None = None,
    probe_agent_fn: Callable[[str], bool] | None = None,
) -> bool:
    is_direct = _VDISPLAY_DIRECT if direct is None else direct
    load_fn = _load_vdisplay_control if load_control is None else load_control
    if is_direct or load_fn():
        return True
    ensure_fn = _ensure_vdisplay_runtime if ensure_runtime is None else ensure_runtime
    if ensure_fn():
        return True
    url_fn = _agent_url if agent_url_fn is None else agent_url_fn
    url = url_fn()
    probe_fn = _probe_agent if probe_agent_fn is None else probe_agent_fn
    return bool(url and probe_fn(url))


def vdisplay_missing_message(
    *,
    agent_url_fn: Callable[[], str | None] | None = None,
    import_error: str | None = None,
) -> str:
    url_fn = _agent_url if agent_url_fn is None else agent_url_fn
    url = url_fn()
    if url:
        return ""
    err = _VDISPLAY_IMPORT_ERROR if import_error is None else import_error
    hint = (
        "Install vdisplay control plane: pip install vdisplay "
        "or set KORU_VDISPLAY_AGENT_URL=http://127.0.0.1:8765"
    )
    if err:
        return f"{hint} ({err})"
    return hint


_IDE_DEFAULT_SOURCE: dict[str, str] = {
    "cursor": "DP-1",
    "windsurf": "DP-1",
    "antigravity": "DP-1",
    "vscode": "DP-1",
    "qoder": "DP-1",
    "jetbrains": "DP-1",
    "pycharm": "DP-1",
    "idea": "DP-1",
}


def simplified_control_likely_insufficient(*, ide: str, plugin_connected: bool = False) -> bool:
    """Heuristic: simplified keyboard/plugin paths are unlikely to work."""
    from koru.integrations.vdisplay.control_policy import (
        simplified_control_likely_insufficient as _simplified_control_policy,
    )

    return _simplified_control_policy(ide=ide, plugin_connected=plugin_connected)


def vdisplay_fallback_enabled(
    *,
    ide: str | None = None,
    plugin_connected: bool = False,
    available_fn: Callable[[], bool] | None = None,
) -> bool:
    """Whether drive may use vdisplay semantic control as fallback."""
    from koru.integrations.vdisplay.control_policy import (
        vdisplay_fallback_enabled as _vdisplay_fallback_policy,
    )

    avail = vdisplay_available if available_fn is None else available_fn
    return _vdisplay_fallback_policy(
        ide=ide,
        plugin_connected=plugin_connected,
        available=avail,
    )


def _capture_matches_requested_ide(
    ide: str,
    *,
    mismatch_fn: Callable[[str], dict[str, Any] | None] | None = None,
) -> bool:
    if os.environ.get("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True
    if mismatch_fn is not None:
        return mismatch_fn(ide=ide) is None
    from koru.integrations import photo_vql_monitor as _photo_vql_monitor

    default_mismatch_fn = getattr(_photo_vql_monitor, "photo_vql_ide_capture_mismatch", None)
    if default_mismatch_fn is not None:
        return default_mismatch_fn(ide=ide) is None
    return True


def _prefer_photo_vql_chat(
    *,
    ide: str = "auto",
    capture_matches: Callable[[str], bool] | None = None,
) -> bool:
    """When set, send_chat uses photo VQL mouse+focus path before os_injector/ide_prompt."""
    from koru.integrations.vdisplay.control_policy import prefer_photo_vql_chat

    match_fn = _capture_matches_requested_ide if capture_matches is None else capture_matches
    return prefer_photo_vql_chat(ide=ide, capture_matches=match_fn)


def _abort_on_desktop_probe_fail() -> bool:
    return os.environ.get("KORU_VDISPLAY_ABORT_ON_PROBE_FAIL", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _resolve_vdisplay_source_for_ide(
    ide: str,
    *,
    probe: dict[str, Any] | None = None,
    canonical_ide_fn: Callable[[str], str] | None = None,
    desktop_probe_fn: Callable[[str], Any] | None = None,
    ide_default_source: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any]]:
    canon_fn = _canonical_ide if canonical_ide_fn is None else canonical_ide_fn
    defaults = _IDE_DEFAULT_SOURCE if ide_default_source is None else ide_default_source
    from koru.integrations.vdisplay.desktop_probe import _desktop_probe

    probe_fn = _desktop_probe if desktop_probe_fn is None else desktop_probe_fn
    from koru.integrations.photo_vql_monitor import (
        resolve_vdisplay_source_for_ide as _resolve_vdisplay_source_impl,
    )

    try:
        return _resolve_vdisplay_source_impl(
            ide,
            canonical_ide=canon_fn,
            desktop_probe=probe_fn,
            probe=probe,
            ide_default_source=defaults,
        )
    except TypeError as exc:
        if "ide_default_source" not in str(exc):
            raise
        from koru.integrations import photo_vql_monitor as _photo_vql_monitor

        previous_defaults = getattr(_photo_vql_monitor, "_IDE_DEFAULT_SOURCE", None)
        _photo_vql_monitor._IDE_DEFAULT_SOURCE = defaults
        try:
            return _resolve_vdisplay_source_impl(
                ide,
                canonical_ide=canon_fn,
                desktop_probe=probe_fn,
                probe=probe,
            )
        finally:
            if previous_defaults is not None:
                _photo_vql_monitor._IDE_DEFAULT_SOURCE = previous_defaults


def _vdisplay_source_for_ide(
    ide: str,
    *,
    resolve_fn: Callable[..., tuple[str, dict[str, Any]]] | None = None,
    canonical_ide_fn: Callable[[str], str] | None = None,
    ide_default_source: dict[str, str] | None = None,
) -> str:
    explicit = os.environ.get("KORU_VDISPLAY_SOURCE", "").strip()
    if explicit:
        return explicit
    res_fn = _resolve_vdisplay_source_for_ide if resolve_fn is None else resolve_fn
    canon_fn = _canonical_ide if canonical_ide_fn is None else canonical_ide_fn
    defaults = _IDE_DEFAULT_SOURCE if ide_default_source is None else ide_default_source
    try:
        src, _probe = res_fn(ide)
        if src:
            os.environ.setdefault("KORU_VDISPLAY_SOURCE", src)
            return src
    except Exception:
        pass
    canon = canon_fn(ide)
    return defaults.get(canon, "DP-1")


def _vdisplay_source(*, source_for_ide_fn: Callable[[str], str] | None = None) -> str:
    explicit = os.environ.get("KORU_VDISPLAY_SOURCE", "").strip()
    if explicit:
        return explicit
    ide = (
        os.environ.get("KORU_DRIVE_IDE")
        or os.environ.get("KORU_AUTOPILOT_INSTANCE")
        or "auto"
    )
    src_fn = _vdisplay_source_for_ide if source_for_ide_fn is None else source_for_ide_fn
    return src_fn(ide)


def _map_source_mismatch_actuation_allowed() -> bool:
    if os.environ.get("KORU_VDISPLAY_ALLOW_MAP_SOURCE_MISMATCH", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True
    from koru.integrations.photo_vql_guard import llm_vision_decision_enabled

    return llm_vision_decision_enabled()


def _annotate_prepare_drive_readiness(
    out: dict[str, Any],
    *,
    map_mismatch_allowed_fn: Callable[[], bool] | None = None,
) -> None:
    reasons: list[str] = []
    if not out.get("ok"):
        reasons.append("prepare_not_ok")
    if out.get("capture_confirmed") is False:
        reasons.append("capture_not_confirmed")
    mismatch_fn = (
        _map_source_mismatch_actuation_allowed
        if map_mismatch_allowed_fn is None
        else map_mismatch_allowed_fn
    )
    if out.get("map_capture_mismatch") and not mismatch_fn():
        reasons.append("map_capture_mismatch")
    if int(out.get("main_vql_layers") or out.get("elements") or 0) <= 0 and not out.get("surface_only_fallback"):
        reasons.append("empty_vql_layers")
    out["drive_ready"] = not reasons
    if reasons:
        out["drive_blocked_reasons"] = reasons
        out["drive_blocked_reason"] = reasons[0]
        if out.get("map_capture_mismatch") and "map_capture_mismatch" in reasons:
            out["map_actuation_ready"] = False
    else:
        out.pop("drive_blocked_reasons", None)
        out.pop("drive_blocked_reason", None)
        if out.get("map_capture_mismatch"):
            out["map_actuation_ready"] = True
