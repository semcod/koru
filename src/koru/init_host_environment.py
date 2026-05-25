"""Host / desktop snapshot written during ``koru --init``.

Produces machine-readable and human-readable summaries so every checkout
documents what that workstation needs for autopilot (plugin vs keyboard
injectors, Wayland vs X11, clipboard helpers, ``/dev/uinput``).
"""


import grp
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

from koru.ide_runtime import build_host_setup_report
from koru.runtime import runtime_dir


def _read_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            key = k.strip()
            val = v.strip().strip('"')
            if key:
                out[key] = val
    return out


def _id_group_names() -> list[str]:
    try:
        proc = subprocess.run(
            ["id", "-Gn"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0 or not proc.stdout:
        return []
    return proc.stdout.strip().split()


def _uinput_snapshot() -> dict[str, Any]:
    path = Path("/dev/uinput")
    if not path.exists():
        return {"present": False}
    try:
        st = path.stat()
    except OSError as exc:
        return {"present": True, "stat_error": str(exc)}
    try:
        group_name = grp.getgrgid(st.st_gid).gr_name
    except (KeyError, OSError):
        group_name = str(st.st_gid)
    return {
        "present": True,
        "mode": stat.filemode(st.st_mode),
        "gid": st.st_gid,
        "group": group_name,
    }


def build_host_environment_report() -> dict[str, Any]:
    """Merge autopilot ``setup-host`` probe with OS/session hints."""
    base = build_host_setup_report()
    os_release = _read_os_release()
    groups = _id_group_names()
    (base.get("session") or "").lower()
    extras: dict[str, Any] = {
        "koru_platform": sys.platform,
        "os_release_id": os_release.get("ID", ""),
        "os_release_pretty": os_release.get("PRETTY_NAME", ""),
        "xdg_session_type": os.environ.get("XDG_SESSION_TYPE", ""),
        "wayland_display": bool(os.environ.get("WAYLAND_DISPLAY")),
        "display": bool(os.environ.get("DISPLAY")),
        "clipboard": {
            "xclip": shutil.which("xclip") is not None,
            "xsel": shutil.which("xsel") is not None,
        },
        "uinput": _uinput_snapshot(),
        "user_in_input_group": "input" in groups,
        "user_groups_sample": groups[:20],
        "recommended_next_steps": _recommended_next_steps(base, groups),
    }
    merged = dict(base)
    merged.update(extras)
    return merged


def _build_backend_steps(
    session: str,
    selected: str | None,
    groups: list[str],
) -> list[str]:
    """Return backend-related next steps based on the active OS strategy."""
    from koruos import resolve_active_os_strategy

    steps: list[str] = []
    if not selected:
        steps.append(
            "No keyboard injector candidate passed the probe — install tools or use the plugin "
            "(see `automated_apt_suggestion` when on Debian/Ubuntu).",
        )

    os_strategy = resolve_active_os_strategy()
    caps = os_strategy.capabilities()
    steps.append(
        f"Active OS strategy: {os_strategy.label} ({os_strategy.id}); "
        f"keyboard={caps.keyboard_tool or '-'}; "
        f"focus={','.join(caps.focus_methods) or '-'}",
    )

    if session == "wayland" or os_strategy.id == "linux-wayland":
        if "integrated_terminal" in caps.focus_methods:
            steps.append(
                "Wayland: run `koru auto` from a terminal *inside* the IDE so "
                "TERM_PROGRAM=vscode is set — Koru can reload without xdotool.",
            )
        steps.append(
            "Wayland: GNOME/KDE often lack wtype's virtual-keyboard protocol — prefer ydotool "
            "(+ ydotoold, `input` group, full re-login) or the IDE extension.",
        )
        if shutil.which("ydotool") and "input" not in groups:
            steps.append(
                "ydotool is on PATH but this login session is not in the `input` group — "
                'run `sudo usermod -aG input "$USER"` then log out and back in.',
            )
    elif session == "x11" or os_strategy.id == "linux-x11":
        steps.append(
            "X11: `xdotool` is the usual keyboard path; optional OS injector uses "
            "`xclip`/`xsel`+Ctrl+V when available (see docs/autopilot-quickstart.md).",
        )

    if session == "wayland" and caps.keyboard_tool == "wtype" and not shutil.which("ydotool"):
        steps.append(
            "If `wtype` fails with “virtual keyboard protocol”, switch to ydotool or the IDE "
            "extension — that error is compositor-side, not a broken wtype install.",
        )
    return steps


def _build_pm_steps(pm: str | None, base: dict[str, Any]) -> list[str]:
    """Return package-manager-related next steps."""
    steps: list[str] = []
    if pm == "apt" and base.get("automated_apt_suggestion"):
        steps.append(
            "Debian/Ubuntu: run `.planfile/.koru/setup-autopilot-host.sh --install --dry-run` "
            "then `--install` when satisfied.",
        )
    elif pm and pm != "apt":
        steps.append(
            f"Package manager hint: {pm} — install xdotool / wtype / ydotool / xclip with that "
            "stack (koru only auto-installs via apt-get).",
        )
    return steps


def _recommended_next_steps(base: dict[str, Any], groups: list[str]) -> list[str]:
    session = (base.get("session") or "").lower()
    selected = base.get("selected_backend")
    pm = base.get("package_manager")

    steps = [
        "Tier 0: install the koru autopilot editor extension and run "
        "`koru autopilot daemon --project .` (works on X11 and Wayland).",
    ]
    steps.extend(_build_backend_steps(session, selected, groups))
    steps.extend(_build_pm_steps(pm, base))
    if not groups:
        steps.append("Could not read `id -Gn` — verify group membership manually if ydotool fails.")
    return steps


def _render_session_section(report: dict[str, Any]) -> list[str]:
    """Render session section of host environment report."""
    return [
        "## Session",
        "",
        f"- **platform:** `{report.get('koru_platform', '')}`",
        f"- **desktop session (injector view):** `{report.get('session', '')}`",
        f"- **XDG_SESSION_TYPE:** `{report.get('xdg_session_type', '')}`",
        f"- **DISPLAY set:** {report.get('display')}",
        f"- **WAYLAND_DISPLAY set:** {report.get('wayland_display')}",
        "",
    ]


def _render_os_section(report: dict[str, Any]) -> list[str]:
    """Render OS section of host environment report."""
    pretty = report.get("os_release_pretty") or report.get("os_release_id")
    if pretty:
        return ["## OS", "", f"- {pretty}", ""]
    return []


def _render_injector_section(report: dict[str, Any]) -> list[str]:
    """Render injector probe section of host environment report."""
    lines = [
        "## Injector probe (same data as `koru autopilot doctor`)",
        "",
        f"- **selected_backend:** `{report.get('selected_backend') or '—'}`",
        "",
    ]
    for b in report.get("backends") or []:
        mark = "✓" if b.get("available") else "✗"
        lines.append(f"- {mark} **{b.get('name')}** — {b.get('reason', '')}")
    lines.append("")
    return lines


def _render_clipboard_section(report: dict[str, Any]) -> list[str]:
    """Render clipboard section of host environment report."""
    clip = report.get("clipboard") or {}
    return [
        "## Clipboard (OS injector paste path)",
        "",
        f"- xclip: {clip.get('xclip')}",
        f"- xsel: {clip.get('xsel')}",
        "",
    ]


def _render_uinput_section(report: dict[str, Any]) -> list[str]:
    """Render /dev/uinput section of host environment report."""
    ui = report.get("uinput") or {}
    if ui.get("present"):
        return [
            "## /dev/uinput",
            "",
            f"- mode: `{ui.get('mode', '')}` group: `{ui.get('group', '')}`",
            f"- user in `input` group (this session): **{report.get('user_in_input_group')}**",
            "",
        ]
    else:
        return ["## /dev/uinput", "", "- device not present (non-Linux or minimal rootfs)", ""]


def _render_next_steps_section(report: dict[str, Any]) -> list[str]:
    """Render recommended next steps section of host environment report."""
    lines = ["## Recommended next steps", ""]
    for step in report.get("recommended_next_steps") or []:
        lines.append(f"1. {step}")
    lines.append("")
    return lines


def _render_human_actions_section(report: dict[str, Any]) -> list[str]:
    """Render human follow-ups section of host environment report."""
    if report.get("human_actions_required"):
        lines = ["## Human follow-ups (from setup-host)", ""]
        for h in report["human_actions_required"]:
            lines.append(f"- {h}")
        lines.append("")
        return lines
    return []


def _render_apt_suggestion_section(report: dict[str, Any]) -> list[str]:
    """Render apt suggestion section of host environment report."""
    if report.get("automated_apt_suggestion"):
        return [
            "## Suggested apt (when packages missing)",
            "",
            "```bash",
            report["automated_apt_suggestion"],
            "```",
            "",
        ]
    return []


def _render_host_environment_md(report: dict[str, Any]) -> str:
    lines = [
        "# Host environment (koru --init)",
        "",
        "Auto-generated snapshot of this machine for **koru autopilot** fallbacks.",
        "Re-run `koru --init --force …` or `koru --init-agent-lane …` to refresh.",
        "",
    ]
    lines.extend(_render_session_section(report))
    lines.extend(_render_os_section(report))
    lines.extend(_render_injector_section(report))
    lines.extend(_render_clipboard_section(report))
    lines.extend(_render_uinput_section(report))
    lines.extend(_render_next_steps_section(report))
    lines.extend(_render_human_actions_section(report))
    lines.extend(_render_apt_suggestion_section(report))
    return "\n".join(lines)


def write_host_environment_bundle(project: Path) -> bool:
    """Write ``host-environment.{json,md}`` under ``.planfile/.koru/``.

    Never raises: a probe failure still leaves a stub so ``koru --init`` can
    complete in sandboxes without ``/proc`` or ``id``.
    """
    project = project.resolve()
    rt = runtime_dir(project)
    rt.mkdir(parents=True, exist_ok=True)
    try:
        report = build_host_environment_report()
    except Exception as exc:  # noqa: BLE001 — best-effort host snapshot
        err = {"probe_error": str(exc), "koru_platform": sys.platform}
        (rt / "host-environment.json").write_text(
            f"{json.dumps(err, indent=2, sort_keys=True)}\n",
            encoding="utf-8",
        )
        (rt / "host-environment.md").write_text(
            f"# Host environment (koru --init)\n\nProbe failed: `{exc}`.\n",
            encoding="utf-8",
        )
        return True
    (rt / "host-environment.json").write_text(
        f"{json.dumps(report, indent=2, sort_keys=True, default=str)}\n",
        encoding="utf-8",
    )
    (rt / "host-environment.md").write_text(_render_host_environment_md(report), encoding="utf-8")
    return True
