"""Human-readable next steps (+ optional TTS) for photo-VQL drive."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


def _truthy(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "")
    if not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def preflight_repo_paths(
    *,
    koru_src: str | None = None,
    imgl_src: str | None = None,
) -> list[str]:
    """Return blocking issues before starting a drive (missing repos / stubs)."""
    issues: list[str] = []
    koru = Path(koru_src or os.environ.get("KORU_SRC", "")).expanduser()
    imgl = Path(imgl_src or os.environ.get("IMGL_SRC", "")).expanduser()
    if not (koru / "koru" / "__init__.py").is_file():
        issues.append(
            f"Brak kodu koru w {koru or '(pusty KORU_SRC)'} — "
            f'export KORU_SRC="$HOME/github/semcod/koru/src"'
        )
    if not (imgl / "imgl" / "__init__.py").is_file():
        issues.append(
            f"Brak pakietu imgl w {imgl or '(pusty IMGL_SRC)'} — "
            f'export IMGL_SRC="$HOME/github/semcod/imgl"'
        )
    return issues


def _drive_retry_cmd(*, ide: str, source: str, root: Path) -> str:
    script = (
        f"cd {root} && bash examples/dev-workflow/koru-drive-photo-vql.sh "
        if root.is_dir()
        else "bash examples/dev-workflow/koru-drive-photo-vql.sh "
    )
    return f'{script}--ide {ide} --source {source} --prompt "hello"'


def _audit_cmd(*, ide: str, root: Path) -> str:
    if root.is_dir():
        return f"cd {root} && bash examples/dev-workflow/koru-audit-last-session.sh --ide {ide}"
    return f"bash examples/dev-workflow/koru-audit-last-session.sh --ide {ide}"


@dataclass(frozen=True)
class _GuidanceContext:
    ide: str
    observe: dict[str, Any]
    reply: dict[str, Any]
    src: str
    resolved: str
    monitors: list[str]
    root: Path
    err: str
    hint: str
    competing: Any
    retry_cmd: str
    audit_cmd: str


def _guidance_success(ctx: _GuidanceContext) -> list[str] | None:
    if ctx.reply.get("ok") is not True:
        return None
    return [
        "Sukces: prompt poszedł do IDE (sprawdź okno PyCharm AI Chat).",
        f"Audit: {ctx.audit_cmd}",
    ]


def _guidance_missing_repo(ctx: _GuidanceContext) -> list[str] | None:
    if not any(
        token in ctx.err
        for token in ("no such file", "modulenotfounderror", "no module named 'koru'")
    ):
        return None
    return [
        "Skrypt jest w repo wronai/vdisplay, nie w semcod/koru.",
        "cd ~/github/wronai/vdisplay",
        'export KORU_SRC="$HOME/github/semcod/koru/src"',
        'export IMGL_SRC="$HOME/github/semcod/imgl"',
        ctx.retry_cmd,
    ]


def _guidance_monitor_not_connected(ctx: _GuidanceContext) -> list[str] | None:
    if not _monitor_not_connected(ctx):
        return None
    fallback = _fallback_monitor(ctx.monitors)
    avail = _available_monitors_label(ctx.monitors)
    return [
        f"Monitor {ctx.src} nie jest podpięty. Dostępne: {avail}.",
        f"Podłącz DP-2 albo użyj --source {fallback} (u Ciebie: DP-1 + HDMI-1).",
        "Sprawdź: vdisplay monitors",
        _drive_retry_cmd(ide=ctx.ide, source=fallback, root=ctx.root),
    ]


def _monitor_not_connected(ctx: _GuidanceContext) -> bool:
    return (
        "monitor not found" in ctx.err
        or "not connected" in ctx.err
        or ("requested monitor" in ctx.err and bool(ctx.monitors))
    )


def _fallback_monitor(monitors: list[str]) -> str:
    return next(
        (m for m in monitors if m.startswith("DP-")),
        monitors[0] if monitors else "DP-1",
    )


def _available_monitors_label(monitors: list[str]) -> str:
    return ", ".join(monitors) if monitors else "(brak — uruchom: vdisplay monitors)"


def _guidance_ide_mismatch(ctx: _GuidanceContext) -> list[str] | None:
    if not _ide_mismatch_detected(ctx):
        return None
    rival = ctx.competing or "Cursor/inne okno"
    steps = [
        f"Na monitorze {ctx.resolved} widać {rival}, a nie PyCharm.",
        f"Kliknij PyCharm na {ctx.resolved} (Alt+Tab / Super+` / klik w pasek tytułu).",
        "Schowaj terminal z tego monitora — jego tekst psuje VQL.",
        "Opcjonalny pre-check: VDISPLAY_CAPTURE_VALIDATE_IDE=jetbrains vdisplay screenshot --source "
        f"{ctx.resolved}",
        "W JSON szukaj capture_validation.capture_confirmed=true i window_titles z „PyCharm”.",
        ctx.retry_cmd,
    ]
    if ctx.hint:
        steps.append(f"Hint systemu: {ctx.hint}")
    return steps


def _ide_mismatch_detected(ctx: _GuidanceContext) -> bool:
    return bool(
        ctx.competing
        or "capture does not match" in ctx.err
        or "ide_window_mismatch" in ctx.err
        or ctx.observe.get("ide_window_warning")
    )


def _guidance_empty_vql(ctx: _GuidanceContext) -> list[str] | None:
    if not _empty_vql_error(ctx.err):
        return None
    return [
        f"Zrzut ekranu na {ctx.resolved} nie zawiera rozpoznawalnego okna IDE.",
        "Podnieś PyCharm na ten monitor i upewnij się, że titlebar jest widoczny.",
        "Zamknij/minimalizuj terminale i Cursor na tym samym monitorze.",
        ctx.retry_cmd,
    ]


def _empty_vql_error(err: str) -> bool:
    return any(token in err for token in ("empty_vql", "no ui elements", "no foreground window title"))


def _guidance_screencast(ctx: _GuidanceContext) -> list[str] | None:
    if not any(
        token in ctx.err
        for token in (
            "portal-screencast",
            "no active session",
            "screencast",
            "host capture failed",
        )
    ):
        return None
    return [
        "Wayland capture wymaga świeżych klatek z browser bridge albo keepera:",
        f"  koru autopilot vdisplay-up --ide {ctx.ide}",
        f"  # w otwartej karcie Chrome/Chromium: Share screen → wybierz {ctx.resolved} → zostaw kartę otwartą",
        f"  vdisplay services status --source {ctx.resolved}",
        "  # fallback keeper, jeśli browser bridge nie jest dostępny:",
        "  vdisplay agent screencast start --force",
        f"  vdisplay agent screencast probe --via-agent --source {ctx.resolved}",
        f"koru autopilot prepare-vdisplay --ide {ctx.ide}",
        ctx.retry_cmd,
    ]


def _guidance_map_capture_mismatch(ctx: _GuidanceContext) -> list[str] | None:
    mm = ctx.observe.get("map_capture_mismatch")
    if not mm:
        probe = ctx.observe.get("desktop_probe") or {}
        if isinstance(probe, dict):
            mm = probe.get("map_capture_mismatch")
    if not isinstance(mm, dict):
        return None
    msg = str(mm.get("message") or "")
    return [
        msg or "GUI map calibrated on a different monitor than capture source.",
        "Recalibrate the map for the capture monitor, or set KORU_VDISPLAY_SOURCE to the map monitor.",
        f"koru autopilot prepare-vdisplay --ide {ctx.ide}",
        ctx.retry_cmd,
    ]


def _guidance_prepare_failed(ctx: _GuidanceContext) -> list[str] | None:
    if not _prepare_failed(ctx):
        return None
    steps = [
        f"Prepare nie przeszedł ({ctx.observe.get('error') or ctx.reply.get('error') or 'nieznany błąd'}).",
        ctx.retry_cmd,
        f"Audit po poprawce: {ctx.audit_cmd}",
    ]
    if ctx.hint:
        steps.append(f"Hint: {ctx.hint}")
    return steps


def _prepare_failed(ctx: _GuidanceContext) -> bool:
    return ctx.observe.get("ok") is False or ctx.reply.get("phase") == "prepare"


def _guidance_drive_failed(ctx: _GuidanceContext) -> list[str]:
    return [
        f"Drive nieudany ({ctx.reply.get('error') or 'sprawdź drive_reply'}).",
        ctx.audit_cmd,
        ctx.retry_cmd,
    ]


_GUIDANCE_BUILDERS: tuple[Callable[[_GuidanceContext], list[str] | None], ...] = (
    _guidance_success,
    _guidance_missing_repo,
    _guidance_monitor_not_connected,
    _guidance_screencast,
    _guidance_map_capture_mismatch,
    _guidance_ide_mismatch,
    _guidance_empty_vql,
    _guidance_prepare_failed,
)


def _build_guidance_context(
    *,
    ide: str,
    observe: dict[str, Any] | None,
    reply: dict[str, Any] | None,
    source: str | None,
    vdisplay_root: str | Path | None,
) -> _GuidanceContext:
    observe = observe or {}
    reply = reply or {}
    src = _resolve_source(source=source, observe=observe)
    root = Path(vdisplay_root or os.environ.get("VDISPLAY_ROOT", "")).expanduser()
    probe = observe.get("desktop_probe") or {}
    monitors = _monitor_names(probe)
    resolved = str(probe.get("resolved_source") or src)
    return _GuidanceContext(
        ide=ide,
        observe=observe,
        reply=reply,
        src=src,
        resolved=resolved,
        monitors=monitors,
        root=root,
        err=_combined_error(observe=observe, reply=reply),
        hint=str(observe.get("hint") or reply.get("hint") or ""),
        competing=observe.get("competing_ide") or reply.get("competing_ide"),
        retry_cmd=_drive_retry_cmd(ide=ide, source=src, root=root),
        audit_cmd=_audit_cmd(ide=ide, root=root),
    )


def _resolve_source(*, source: str | None, observe: dict[str, Any]) -> str:
    return str(source or observe.get("source") or os.environ.get("KORU_VDISPLAY_SOURCE") or "DP-1")


def _monitor_names(probe: Any) -> list[str]:
    if not isinstance(probe, dict):
        return []
    monitors = probe.get("monitor_names") or []
    return [str(m) for m in monitors]


def _combined_error(*, observe: dict[str, Any], reply: dict[str, Any]) -> str:
    return str(observe.get("error") or reply.get("error") or "").lower()


def build_user_guidance(
    *,
    ide: str,
    observe: dict[str, Any] | None = None,
    reply: dict[str, Any] | None = None,
    source: str | None = None,
    vdisplay_root: str | Path | None = None,
) -> list[str]:
    """Actionable steps for the operator based on prepare/drive outcome."""
    ctx = _build_guidance_context(
        ide=ide,
        observe=observe,
        reply=reply,
        source=source,
        vdisplay_root=vdisplay_root,
    )
    for builder in _GUIDANCE_BUILDERS:
        steps = builder(ctx)
        if steps is not None:
            return steps
    return _guidance_drive_failed(ctx)


def format_user_guidance(lines: list[str]) -> str:
    body = "\n".join(f"  {idx}. {line}" for idx, line in enumerate(lines, start=1))
    return f"\n=== CO TERAZ ZROBIĆ (USER) ===\n{body}\n==============================\n"


def speak_user_guidance(lines: list[str], *, title: str = "Koru photo-VQL") -> None:
    """Optional spoken + desktop notification for the first actionable lines."""
    if not lines or not _user_guidance_speech_enabled():
        return
    short = ". ".join(line.rstrip(".") for line in lines[:2])
    _notify_user_guidance(title=title, text=short)
    _speak_user_guidance_text(short)


def _user_guidance_speech_enabled() -> bool:
    return _truthy("KORU_VDISPLAY_USER_TTS") or _truthy("KORU_VDISPLAY_SPEAK")


def _notify_user_guidance(*, title: str, text: str) -> None:
    if shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", title, text[:240]],
                check=False,
                timeout=5,
                capture_output=True,
            )
        except Exception:
            pass


def _speak_user_guidance_text(text: str) -> None:
    for cmd, args in (
        ("spd-say", ["-r", "0", "-t", text[:400]]),
        ("espeak", ["-s", "150", text[:400]]),
        ("espeak-ng", ["-s", "150", text[:400]]),
    ):
        if shutil.which(cmd):
            try:
                subprocess.run([cmd, *args], check=False, timeout=30, capture_output=True)
            except Exception:
                pass
            break


def emit_user_guidance(
    *,
    ide: str,
    observe: dict[str, Any] | None = None,
    reply: dict[str, Any] | None = None,
    source: str | None = None,
    vdisplay_root: str | Path | None = None,
    stream: Any | None = None,
) -> list[str]:
    """Print guidance, optionally speak/notify; return the step lines."""
    import sys

    out = stream or sys.stderr
    lines = build_user_guidance(
        ide=ide,
        observe=observe,
        reply=reply,
        source=source,
        vdisplay_root=vdisplay_root,
    )
    print(format_user_guidance(lines), file=out)
    speak_user_guidance(lines)
    return lines


__all__ = [
    "build_user_guidance",
    "emit_user_guidance",
    "format_user_guidance",
    "preflight_repo_paths",
    "speak_user_guidance",
]
