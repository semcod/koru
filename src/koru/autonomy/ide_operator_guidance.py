"""Actionable operator instructions for IDE identification and chat control."""

from __future__ import annotations

from typing import Any, Literal

from koruide.ide import TerminalKind

_IDE_LABELS: dict[str, str] = {
    "antigravity": "Antigravity",
    "cursor": "Cursor",
    "jetbrains": "JetBrains IDE",
    "vscode": "VS Code",
    "vscodium": "VSCodium",
    "windsurf": "Windsurf",
    "zed": "Zed",
}


def ide_label(ide: str | None) -> str:
    if not ide:
        return "target IDE"
    key = ide.strip().lower()
    return _IDE_LABELS.get(key, key)


def terminal_kind_label(kind: TerminalKind) -> str:
    if kind == "integrated":
        return "integrated IDE terminal"
    if kind == "ide_adjacent":
        return "system/external terminal (IDE ancestor detected)"
    return "system shell (no IDE terminal markers)"


def chat_focus_operator_steps(
    ide: str | None,
    *,
    context: Literal["drive", "focus", "paste_probe", "submit", "calibrate"] = "drive",
) -> list[str]:
    """Numbered steps for the human operator before Koru drives the IDE chat."""
    label = ide_label(ide)
    steps = [
        f"Bring {label} to the foreground with this project workspace open.",
        "Open the chat / AI panel (sidebar icon or Command Palette → chat focus).",
        "Click inside the chat input field until the text cursor blinks there "
        "(not in a file editor, terminal, or search box).",
    ]
    if context == "paste_probe":
        steps.append(
            "Keep the chat input focused, then retry the drive or calibration — "
            "VSCodium/Wayland webviews often block clipboard probes when focus is wrong."
        )
    elif context == "submit":
        steps.append(
            "Press Enter / Send in the chat to submit the pending prompt manually."
        )
    elif context == "calibrate":
        steps.append(
            "Run Command Palette → „koru: Calibrate chat probe ladder” only after the "
            "chat input is focused."
        )
    elif context == "focus":
        steps.append("Retry the drive once the chat input is visibly focused.")
    else:
        steps.append("Retry the Koru drive after focus is confirmed.")
    return steps


def manual_send_operator_steps(ide: str | None, *, ticket_id: str | None = None) -> list[str]:
    steps = chat_focus_operator_steps(ide, context="submit")
    if ticket_id:
        steps.append(
            f"If the ticket queue should continue, ensure {ticket_id} leaves waiting_input "
            "after the manual send (or close/skip the ticket)."
        )
    return steps


def lane_mismatch_operator_steps(
    *,
    terminal_ide: str | None,
    target_ide: str,
    terminal_kind: TerminalKind,
    lane: str | None = None,
) -> list[str]:
    target = ide_label(target_ide)
    host = ide_label(terminal_ide)
    steps: list[str] = []
    if terminal_kind == "integrated" and terminal_ide and terminal_ide != target_ide:
        steps.append(
            f"This shell is inside {host}, but autopilot lane targets {target} "
            + (f"({lane})" if lane else "")
            + "."
        )
        steps.append(f"Run `coru {target_ide} auto` or open {target}'s integrated terminal.")
        steps.append(f"Or export KORU_AUTOPILOT_INSTANCE={target_ide} and restart.")
    elif terminal_kind == "ide_adjacent" and terminal_ide:
        steps.append(
            f"Shell is external but was spawned under {host}; lane targets {target}."
        )
        steps.append(
            f"Prefer {target}'s integrated terminal, or run `coru {target_ide} auto` explicitly."
        )
    else:
        steps.append(f"Autopilot lane targets {target}" + (f" ({lane})" if lane else "") + ".")
        steps.append(f"Open {target} and run `coru {target_ide} auto` from its terminal.")
    steps.append("Cross-IDE control override: KORU_AUTOPILOT_ALLOW_CROSS_IDE=1 (explicit opt-in).")
    return steps


def classify_drive_failure_guidance(
    reply: dict[str, Any],
    *,
    ide: str | None = None,
) -> list[str] | None:
    """Map a daemon drive reply to operator steps, if recognizable."""
    message = str(reply.get("message") or "").lower()
    paste_reason = str(reply.get("paste_failure_reason") or reply.get("reason") or "").lower()
    verification = str(reply.get("verification") or "").lower()
    combined = f"{message} {paste_reason}"

    if "not focused" in combined or "focus_open" in combined and not reply.get("opened"):
        return chat_focus_operator_steps(ide, context="focus")
    if any(
        token in combined
        for token in (
            "probe inconclusive",
            "sentinel unchanged",
            "terminal-risk",
            "paste command failed",
            "clipboard unreadable",
        )
    ):
        return chat_focus_operator_steps(ide, context="paste_probe")
    if verification in {"submit_unverified", "submit_failed"} or (
        reply.get("submitted") is False and reply.get("delivered")
    ):
        return manual_send_operator_steps(ide)
    if verification == "input_busy":
        return [
            *chat_focus_operator_steps(ide, context="submit"),
            "Clear or send the existing un-submitted text in the chat input before retrying.",
        ]
    return None


def format_operator_guidance_block(
    lines: list[str],
    *,
    title: str = "Operator — IDE chat control",
) -> list[str]:
    if not lines:
        return []
    out = [f"--- {title} ---"]
    for idx, line in enumerate(lines, start=1):
        out.append(f"  {idx}) {line}")
    out.append("---")
    return out


def emit_operator_guidance(
    lines: list[str],
    *,
    title: str = "Operator — IDE chat control",
    stream: Any | None = None,
) -> None:
    import sys

    sink = stream or sys.stderr
    for line in format_operator_guidance_block(lines, title=title):
        print(line, file=sink)


__all__ = [
    "TerminalKind",
    "chat_focus_operator_steps",
    "classify_drive_failure_guidance",
    "emit_operator_guidance",
    "format_operator_guidance_block",
    "ide_label",
    "lane_mismatch_operator_steps",
    "manual_send_operator_steps",
    "terminal_kind_label",
]
