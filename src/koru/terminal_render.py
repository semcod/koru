"""Terminal rendering utilities for Koru CLI output.

Renders Markdown content cleanly for interactive terminal sessions using Rich
when available, with fallback to clean plaintext formatting, while respecting
pipe redirection, dumb terminals, NO_COLOR, --raw, and --plain modes.
"""

from __future__ import annotations

import os
import re
import sys
from typing import TextIO


def is_interactive_terminal(stream: TextIO | None = None) -> bool:
    """Check if stream is an interactive terminal capable of formatted display."""
    target = stream or sys.stdout
    if not hasattr(target, "isatty") or not target.isatty():
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return True


def strip_markdown(text: str) -> str:
    """Convert markdown text to clean readable plain text."""
    lines = []
    for line in text.splitlines():
        # Strip header markers (# Title -> Title)
        h_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h_match:
            lines.append(h_match.group(2))
            continue

        # Convert bullet points (- **Key**: `val` ->   - Key: val)
        b_match = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        if b_match:
            indent = b_match.group(1)
            content = b_match.group(2)
            content = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)
            content = re.sub(r"\*([^*]+)\*", r"\1", content)
            content = re.sub(r"`([^`]+)`", r"\1", content)
            lines.append(f"{indent}  • {content}")
            continue

        # General markdown stripping
        cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
        lines.append(cleaned)

    return "\n".join(lines)


def render_markdown(
    md_text: str,
    *,
    force_raw: bool = False,
    force_plain: bool = False,
    stream: TextIO | None = None,
) -> None:
    """Render markdown text to stream using Rich, raw, or plain formatting.

    Args:
        md_text: The markdown-formatted string.
        force_raw: If True, always output raw markdown without formatting.
        force_plain: If True, output plain text without ANSI or markdown syntax.
        stream: Target text stream (defaults to sys.stdout).
    """
    target = stream or sys.stdout

    # Explicit raw mode requested
    if force_raw:
        target.write(md_text if md_text.endswith("\n") else md_text + "\n")
        target.flush()
        return

    # Plain text mode requested
    if force_plain:
        plain_text = strip_markdown(md_text)
        target.write(plain_text if plain_text.endswith("\n") else plain_text + "\n")
        target.flush()
        return

    # Pipe / non-interactive redirection defaults to raw markdown for composability
    if not is_interactive_terminal(target):
        target.write(md_text if md_text.endswith("\n") else md_text + "\n")
        target.flush()
        return

    # Interactive TTY: try Rich rendering
    no_color = bool(os.environ.get("NO_COLOR"))
    try:
        from rich.console import Console
        from rich.markdown import Markdown

        console = Console(
            file=target,
            force_terminal=True,
            no_color=no_color,
            highlight=False,
        )
        console.print(Markdown(md_text))
        return
    except ImportError:
        # Fallback if rich is somehow unavailable
        plain = strip_markdown(md_text)
        target.write(plain if plain.endswith("\n") else plain + "\n")
        target.flush()
