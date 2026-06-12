"""Human-readable next steps (+ optional TTS) for photo-VQL drive."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


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
            f"export KORU_SRC=\"$HOME/github/semcod/koru/src\""
        )
    if not (imgl / "imgl" / "__init__.py").is_file():
        issues.append(
            f"Brak pakietu imgl w {imgl or '(pusty IMGL_SRC)'} — "
            f"export IMGL_SRC=\"$HOME/github/semcod/imgl\""
        )
    return issues


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

    def _retry_cmd(source_name: str) -> str:
        cmd = (
            f"cd {root} && bash examples/dev-workflow/koru-drive-photo-vql.sh "
            f'--ide {ide} --source {source_name} --prompt "hello"'
            if root.is_dir()
            else f'bash examples/dev-workflow/koru-drive-photo-vql.sh --ide {ide} --source {source_name} --prompt "hello"'
        )
        return cmd

    audit_cmd = (
        f"cd {root} && bash examples/dev-workflow/koru-audit-last-session.sh --ide {ide}"
        if root.is_dir()
        else f"bash examples/dev-workflow/koru-audit-last-session.sh --ide {ide}"
    )
    retry_cmd = _retry_cmd(src)

    if reply.get("ok") is True:
        return [
            "Sukces: prompt poszedł do IDE (sprawdź okno PyCharm AI Chat).",
            f"Audit: {audit_cmd}",
        ]

    err = str(observe.get("error") or reply.get("error") or "").lower()
    hint = str(observe.get("hint") or reply.get("hint") or "")
    competing = observe.get("competing_ide") or reply.get("competing_ide")

    steps: list[str] = []

    if "no such file" in err or "modulenotfounderror" in err or "no module named 'koru'" in err:
        steps.extend(
            [
                "Skrypt jest w repo wronai/vdisplay, nie w semcod/koru.",
                "cd ~/github/wronai/vdisplay",
                "export KORU_SRC=\"$HOME/github/semcod/koru/src\"",
                "export IMGL_SRC=\"$HOME/github/semcod/imgl\"",
                retry_cmd,
            ]
        )
        return steps

    if (
        "monitor not found" in err
        or "not connected" in err
        or ("requested monitor" in err and monitors)
    ):
        # Prefer non-HDMI external panel when PyCharm is usually docked (DP-1 over HDMI-1).
        fallback = next((m for m in monitors if m.startswith("DP-")), monitors[0] if monitors else "DP-1")
        avail = ", ".join(monitors) if monitors else "(brak — uruchom: vdisplay monitors)"
        steps.extend(
            [
                f"Monitor {src} nie jest podpięty. Dostępne: {avail}.",
                f"Podłącz DP-2 albo użyj --source {fallback} (u Ciebie: DP-1 + HDMI-1).",
                f"Sprawdź: vdisplay monitors",
                _retry_cmd(fallback),
            ]
        )
        return steps

    if competing or "capture does not match" in err or "ide_window_mismatch" in err or observe.get("ide_window_warning"):
        rival = competing or "Cursor/inne okno"
        steps.extend(
            [
                f"Na monitorze {resolved} widać {rival}, a nie PyCharm.",
                f"Kliknij PyCharm na {resolved} (Alt+Tab / Super+` / klik w pasek tytułu).",
                "Schowaj terminal z tego monitora — jego tekst psuje VQL.",
                "Opcjonalny pre-check: VDISPLAY_CAPTURE_VALIDATE_IDE=jetbrains vdisplay screenshot --source "
                f"{resolved}",
                "W JSON szukaj capture_validation.capture_confirmed=true i window_titles z „PyCharm”.",
                retry_cmd,
            ]
        )
        if hint:
            steps.append(f"Hint systemu: {hint}")
        return steps

    if "empty_vql" in err or "no ui elements" in err or "no foreground window title" in err:
        steps.extend(
            [
                f"Zrzut ekranu na {resolved} nie zawiera rozpoznawalnego okna IDE.",
                "Podnieś PyCharm na ten monitor i upewnij się, że titlebar jest widoczny.",
                "Zamknij/minimalizuj terminale i Cursor na tym samym monitorze.",
                retry_cmd,
            ]
        )
        return steps

    if observe.get("ok") is False or reply.get("phase") == "prepare":
        steps.extend(
            [
                f"Prepare nie przeszedł ({observe.get('error') or reply.get('error') or 'nieznany błąd'}).",
                retry_cmd,
                f"Audit po poprawce: {audit_cmd}",
            ]
        )
        if hint:
            steps.append(f"Hint: {hint}")
        return steps

    steps.extend(
        [
            f"Drive nieudany ({reply.get('error') or 'sprawdź drive_reply'}).",
            audit_cmd,
            retry_cmd,
        ]
    )
    return steps


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
