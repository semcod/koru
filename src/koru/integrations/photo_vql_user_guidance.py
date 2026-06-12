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
    if not (
        "monitor not found" in ctx.err
        or "not connected" in ctx.err
        or ("requested monitor" in ctx.err and ctx.monitors)
    ):
        return None
    fallback = next(
        (m for m in ctx.monitors if m.startswith("DP-")),
        ctx.monitors[0] if ctx.monitors else "DP-1",
    )
    avail = ", ".join(ctx.monitors) if ctx.monitors else "(brak — uruchom: vdisplay monitors)"
    return [
        f"Monitor {ctx.src} nie jest podpięty. Dostępne: {avail}.",
        f"Podłącz DP-2 albo użyj --source {fallback} (u Ciebie: DP-1 + HDMI-1).",
        "Sprawdź: vdisplay monitors",
        _drive_retry_cmd(ide=ctx.ide, source=fallback, root=ctx.root),
    ]


def _guidance_ide_mismatch(ctx: _GuidanceContext) -> list[str] | None:
    if not (
        ctx.competing
        or "capture does not match" in ctx.err
        or "ide_window_mismatch" in ctx.err
        or ctx.observe.get("ide_window_warning")
    ):
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


def _guidance_empty_vql(ctx: _GuidanceContext) -> list[str] | None:
    if not any(
        token in ctx.err
        for token in ("empty_vql", "no ui elements", "no foreground window title")
    ):
        return None
    return [
        f"Zrzut ekranu na {ctx.resolved} nie zawiera rozpoznawalnego okna IDE.",
        "Podnieś PyCharm na ten monitor i upewnij się, że titlebar jest widoczny.",
        "Zamknij/minimalizuj terminale i Cursor na tym samym monitorze.",
        ctx.retry_cmd,
    ]


def _guidance_prepare_failed(ctx: _GuidanceContext) -> list[str] | None:
    if not (ctx.observe.get("ok") is False or ctx.reply.get("phase") == "prepare"):
        return None
    steps = [
        f"Prepare nie przeszedł ({ctx.observe.get('error') or ctx.reply.get('error') or 'nieznany błąd'}).",
        ctx.retry_cmd,
        f"Audit po poprawce: {ctx.audit_cmd}",
    ]
    if ctx.hint:
        steps.append(f"Hint: {ctx.hint}")
    return steps


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
    _guidance_ide_mismatch,
    _guidance_empty_vql,
    _guidance_prepare_failed,
)


def build_user_guidance(
    *,
    ide: str,
    observe: dict[str, Any] | None = None,
    reply: dict[str, Any] | None = None,
    source: str | None = None,
    vdisplay_root: str | Path | None = None,
) -> list[str]:
    """Actionable steps for the operator based on prepare/drive outcome."""
    observe = observe or {}
    reply = reply or {}
    src = source or observe.get("source") or os.environ.get("KORU_VDISPLAY_SOURCE") or "DP-1"
    root = Path(vdisplay_root or os.environ.get("VDISPLAY_ROOT", "")).expanduser()
    probe = observe.get("desktop_probe") or {}
    monitors = probe.get("monitor_names") or []
    resolved = probe.get("resolved_source") or src

    ctx = _GuidanceContext(
        ide=ide,
        observe=observe,
        reply=reply,
        src=src,
        resolved=resolved,
        monitors=list(monitors),
        root=root,
        err=str(observe.get("error") or reply.get("error") or "").lower(),
        hint=str(observe.get("hint") or reply.get("hint") or ""),
        competing=observe.get("competing_ide") or reply.get("competing_ide"),
        retry_cmd=_drive_retry_cmd(ide=ide, source=src, root=root),
        audit_cmd=_audit_cmd(ide=ide, root=root),
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
    if not lines or not _truthy("KORU_VDISPLAY_USER_TTS") and not _truthy("KORU_VDISPLAY_SPEAK"):
        return
    short = ". ".join(line.rstrip(".") for line in lines[:2])
    if shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", title, short[:240]],
                check=False,
                timeout=5,
                capture_output=True,
            )
        except Exception:
            pass
    for cmd, args in (
        ("spd-say", ["-r", "0", "-t", short[:400]]),
        ("espeak", ["-s", "150", short[:400]]),
        ("espeak-ng", ["-s", "150", short[:400]]),
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
