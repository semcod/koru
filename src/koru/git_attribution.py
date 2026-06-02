"""Git attribution helpers for koru-assisted work."""

from __future__ import annotations

import os
import stat
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

KORU_AGENT_NAME = "Koru Agent"
KORU_AGENT_EMAIL = "agent@coru.dev"
KORU_AGENT_COAUTHOR = f"{KORU_AGENT_NAME} <{KORU_AGENT_EMAIL}>"
KORU_AGENT_COAUTHOR_TRAILER = f"Co-authored-by: {KORU_AGENT_COAUTHOR}"

_HOOK_START = "# >>> koru-agent-coauthor >>>"
_HOOK_END = "# <<< koru-agent-coauthor <<<"


@dataclass(frozen=True)
class CoauthorHookResult:
    status: str
    hook_path: Path | None = None
    detail: str = ""


from koru.env_flags import env_disabled as _env_disabled


def _git_dir(project: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "--git-dir"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = project / path
    return path.resolve()


def _managed_block() -> str:
    return f"""{_HOOK_START}
# Keep human or IDE commits attributed to the person making the commit, while
# crediting koru as the assisting agent on GitHub.
koru_msg_file="$1"
if [ -n "$koru_msg_file" ] && [ -f "$koru_msg_file" ]; then
  if ! grep -Fqx "{KORU_AGENT_COAUTHOR_TRAILER}" "$koru_msg_file"; then
    printf '\\n{KORU_AGENT_COAUTHOR_TRAILER}\\n' >> "$koru_msg_file"
  fi
fi
{_HOOK_END}
"""


def _strip_managed_block(text: str) -> str:
    start = text.find(_HOOK_START)
    end = text.find(_HOOK_END)
    if start == -1 or end == -1:
        return text
    end += len(_HOOK_END)
    while end < len(text) and text[end] in "\r\n":
        end += 1
    return text[:start].rstrip() + ("\n\n" if text[:start].strip() else "") + text[end:].lstrip()


def _is_shell_hook(text: str) -> bool:
    first_line = text.splitlines()[0] if text.splitlines() else ""
    return (
        not first_line.startswith("#!")
        or "sh" in first_line
        or "bash" in first_line
        or "zsh" in first_line
    )


def install_koru_agent_coauthor_hook(
    project: Path,
    *,
    stdio_info: Callable[..., None] | None = None,
    stdio_format: str = "human",
) -> CoauthorHookResult:
    """Install a repo-local prepare-commit-msg hook that adds koru co-authorship.

    The hook preserves the user's normal Git author and appends a standard
    GitHub co-author trailer. It is intentionally repo-local and opt-out via
    ``KORU_AGENT_COAUTHOR=0``.
    """
    if _env_disabled("KORU_AGENT_COAUTHOR"):
        return CoauthorHookResult(status="disabled")

    git_dir = _git_dir(project)
    if git_dir is None:
        return CoauthorHookResult(status="no_git_repo")

    hooks_dir = git_dir / "hooks"
    hook_path = hooks_dir / "prepare-commit-msg"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    existing = hook_path.read_text(encoding="utf-8") if hook_path.exists() else ""
    if existing and not _is_shell_hook(existing):
        result = CoauthorHookResult(
            status="skipped_non_shell_hook",
            hook_path=hook_path,
            detail="existing prepare-commit-msg hook is not a shell script",
        )
        if stdio_info is not None:
            stdio_info(
                "koru autonomous: [!] skipped git co-author hook: " + result.detail,
                fmt=stdio_format,
            )
        return result

    base = _strip_managed_block(existing).rstrip()
    if not base:
        base = "#!/bin/sh"
    new_text = base + "\n\n" + _managed_block()
    hook_path.write_text(new_text, encoding="utf-8")
    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    result = CoauthorHookResult(status="installed", hook_path=hook_path)
    if stdio_info is not None:
        stdio_info(
            f"koru autonomous: git co-author hook active ({KORU_AGENT_COAUTHOR_TRAILER})",
            fmt=stdio_format,
        )
    return result


__all__ = [
    "CoauthorHookResult",
    "KORU_AGENT_COAUTHOR",
    "KORU_AGENT_COAUTHOR_TRAILER",
    "install_koru_agent_coauthor_hook",
]
