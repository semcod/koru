"""Thin adapter to imgl control layer (nlp2imgl / rest2imgl)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_IMGL_DIRECT = False
_IMGL_IMPORT_ERROR: str | None = None

try:
    from nlp2imgl.control import apply_nl_with_diag as _apply_nl_with_diag
    from nlp2imgl.control import default_image_path as _default_image_path
    from nlp2imgl.control import default_window as _default_window
    from nlp2imgl.control import doctor_capture as _doctor_capture

    _IMGL_DIRECT = True
except ImportError as exc:
    _IMGL_IMPORT_ERROR = str(exc)


_UI_PROMPT_RE = (
    r"\b(kliknij|click|tap|wpisz|wprowadź|wprowadz|type|"
    r"ctrl\+enter|control\+enter|naciśnij enter|nacisnij enter|"
    r"naciśnij ctrl|nacisnij ctrl|press enter|"
    r"zrzut|capture|screenshot|akcje|actions|katalog|catalog)\b"
)


def imgl_available() -> bool:
    if _IMGL_DIRECT:
        return True
    return bool(os.environ.get("KORU_IMGL_REST_URL", "").strip())


def imgl_missing_message() -> str:
    rest = os.environ.get("KORU_IMGL_REST_URL", "").strip()
    if rest:
        return ""
    hint = (
        "Install imgl control layer: "
        "pip install -e ~/github/semcod/imgl/packages/nlp2imgl "
        "or set KORU_IMGL_REST_URL=http://127.0.0.1:8219"
    )
    if _IMGL_IMPORT_ERROR:
        return f"{hint} ({_IMGL_IMPORT_ERROR})"
    return hint


def imgl_fallback_enabled() -> bool:
    raw = os.environ.get("KORU_IMGL_FALLBACK", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def imgl_desktop_transport_enabled() -> bool:
    raw = os.environ.get("KORU_IMGL_DESKTOP", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def default_image_path() -> Path:
    if _IMGL_DIRECT:
        return _default_image_path()
    raw = os.environ.get("KORU_IMGL_IMAGE", "/tmp/koru-imgl-screen.png").strip()
    return Path(raw).expanduser()


def default_window() -> str | None:
    if _IMGL_DIRECT:
        return _default_window()
    raw = os.environ.get("KORU_IMGL_WINDOW", "region-bottom").strip()
    return raw or None


def is_ui_prompt(prompt: str) -> bool:
    import re

    return bool(re.search(_UI_PROMPT_RE, prompt, re.IGNORECASE))


def resolve_image(*, refresh: bool = True) -> str:
    """Resolve screenshot path; optional refresh via dsl2imgl CAPTURE."""
    path = default_image_path()
    if path.is_file() and not refresh:
        return str(path)
    if refresh:
        try:
            from dsl2imgl import dispatch

            interactive = os.environ.get("KORU_IMGL_CAPTURE_INTERACTIVE", "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            cmd = "CAPTURE INTERACTIVE" if interactive else "CAPTURE"
            result = dispatch(cmd)
            if result.ok and result.data.get("path"):
                captured = Path(str(result.data["path"])).expanduser()
                if captured.is_file():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(captured.read_bytes())
                    from imgl.freshness import mark_capture_fresh

                    mark_capture_fresh(path)
                    return str(path)
        except ImportError:
            pass
    if not path.is_file():
        raise RuntimeError(
            f"screenshot missing: {path} — run: imgl capture --interactive -o {path}"
        )
    return str(path)


def _rest_url() -> str:
    return os.environ.get("KORU_IMGL_REST_URL", "http://127.0.0.1:8219").rstrip("/")


def _dry_run() -> bool:
    return os.environ.get("KORU_IMGL_DRY_RUN", "").strip().lower() in {"1", "true", "yes", "on"}


def diagnostics_enabled() -> bool:
    from imgl.autodiag import diagnostics_enabled as _enabled

    return _enabled()


def doctor_capture(
    image: str | Path | None = None,
    *,
    locale: str = "pl",
) -> dict[str, Any]:
    if _IMGL_DIRECT:
        img = str(image) if image else str(default_image_path())
        return _doctor_capture(img, locale=locale)
    return _rest_doctor(str(image) if image else str(default_image_path()), locale=locale)


def execute_nl(
    prompt: str,
    *,
    image: str | None = None,
    window: str | None = None,
    execute: bool = True,
    dry_run: bool | None = None,
    with_diagnostics: bool | None = None,
) -> dict[str, Any]:
    """Run one NL prompt through nlp2imgl (with optional autodiag)."""
    if not imgl_available():
        return {"ok": False, "backend": "imgl", "error": imgl_missing_message()}

    effective_dry = _dry_run() if dry_run is None else dry_run
    do_execute = execute and not effective_dry
    img = image or resolve_image(refresh="capture" in prompt.lower() or "zrzut" in prompt.lower())
    win = window if window is not None else default_window()
    do_diag = diagnostics_enabled() if with_diagnostics is None else with_diagnostics

    if _IMGL_DIRECT:
        return _apply_nl_with_diag(
            prompt,
            image=img,
            window=win,
            execute=do_execute,
            dry_run=effective_dry,
            with_diagnostics=do_diag,
        )

    body = json.dumps(
        {
            "prompt": prompt,
            "image": img,
            "window": win,
            "execute": do_execute,
            "with_diagnostics": do_diag,
        }
    ).encode("utf-8")
    endpoint = "/v1/nl/diag" if do_diag else "/v1/nl"
    req = urllib.request.Request(
        f"{_rest_url()}{endpoint}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return {"ok": False, "backend": "imgl", "error": str(exc)}

    if do_diag:
        return payload
    inner = payload.get("result") or payload
    return {
        "ok": bool(inner.get("ok")),
        "backend": "imgl",
        "verb": inner.get("verb"),
        "output": inner.get("output"),
        "data": inner.get("data") or {},
        "error": inner.get("error"),
    }


def _rest_doctor(image: str, *, locale: str) -> dict[str, Any]:
    body = json.dumps({"image": image, "locale": locale}).encode("utf-8")
    req = urllib.request.Request(
        f"{_rest_url()}/v1/doctor",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("capture") or payload


def _submit_key_for_ide(ide: str, submit: bool) -> str:
    if not submit:
        return ""
    from koru.autonomous_cycle_gate import effective_ide_control_submit

    if not effective_ide_control_submit(submit=submit, ide=ide):
        return ""
    if ide.strip().lower() == "cursor":
        return "ctrl+Return"
    return "Return"


def send_chat(
    prompt: str,
    *,
    ide: str,
    submit: bool,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Vision-guided chat drive: TYPE into Chat input, optional KEY submit."""
    effective_dry = _dry_run() if dry_run is None else dry_run
    if effective_dry:
        return {
            "ok": True,
            "backend": "imgl",
            "dry_run": True,
            "ide": ide,
            "chars": len(prompt),
            "submit": submit,
        }

    type_result = execute_nl(
        f"wpisz {prompt} w Chat input",
        execute=True,
        dry_run=False,
    )
    if not type_result.get("ok"):
        type_result.setdefault("fallback_from", "plugin")
        return type_result

    key = _submit_key_for_ide(ide, submit)
    if not key:
        type_result["submitted"] = False
        type_result["fallback_from"] = "plugin"
        return type_result

    time.sleep(0.2)
    key_prompt = "naciśnij ctrl+enter" if "ctrl" in key.lower() else "naciśnij enter"
    key_result = execute_nl(key_prompt, execute=True, dry_run=False)
    ok = bool(key_result.get("ok"))
    return {
        "ok": ok,
        "backend": "imgl",
        "message": key_result.get("output") or key_result.get("error") or "",
        "type": "drive" if ok else "error",
        "fallback_from": "plugin",
        "type_step": type_result,
        "key_step": key_result,
        "submitted": ok,
        "ide": ide,
    }


__all__ = [
    "default_image_path",
    "default_window",
    "diagnostics_enabled",
    "doctor_capture",
    "execute_nl",
    "imgl_available",
    "imgl_desktop_transport_enabled",
    "imgl_fallback_enabled",
    "imgl_missing_message",
    "is_ui_prompt",
    "resolve_image",
    "send_chat",
]
