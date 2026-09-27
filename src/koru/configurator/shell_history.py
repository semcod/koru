"""Readline auto-completion and persistent command history for koru config shell."""

from __future__ import annotations

import atexit
from collections.abc import Callable
from pathlib import Path

from koruide.ide import autopilot_ide_choices

from koru.configurator.features import _TOGGLEABLE_FEATURES

try:
    import readline
except ImportError:
    readline = None  # type: ignore[assignment]


_DEFAULT_COMMANDS = (
    "ide na ",
    "zmien ide na ",
    "port na ",
    "zmien port na ",
    "host na ",
    "model na ",
    "prosty model na ",
    "kolejka na ",
    "wlacz lan",
    "wylacz lan",
    "wlacz auto-port",
    "wylacz auto-port",
    "wlacz ",
    "wylacz ",
    "pokaz",
    "tabela",
    "status",
    "exit",
    "wyjdz",
)


class ConfigCompleter:
    """Readline tab-completion callback for the interactive configurator."""

    def __init__(self) -> None:
        self._ide_choices = autopilot_ide_choices()
        self._features = _TOGGLEABLE_FEATURES

    def complete(self, text: str, state: int) -> str | None:
        matches = self.get_candidates(text)
        if state < len(matches):
            return matches[state]
        return None

    def get_candidates(self, line_prefix: str) -> list[str]:
        prefix = line_prefix.strip().lower().replace("ł", "l")
        candidates: list[str] = []

        # If typing after "ide na " or "zmien ide na "
        for trigger in ("ide na ", "zmien ide na ", "ide to ", "set ide to "):
            if prefix.startswith(trigger):
                sub = prefix[len(trigger):].strip()
                for ide in self._ide_choices:
                    if ide.startswith(sub):
                        candidates.append(f"{trigger}{ide}")
                return candidates

        # If typing after "wlacz " or "wylacz "
        for trigger in ("wlacz ", "wylacz ", "enable ", "disable "):
            if prefix.startswith(trigger):
                sub = prefix[len(trigger):].strip()
                pool = list(self._features) + ["lan", "auto-port"]
                for item in pool:
                    if item.startswith(sub):
                        candidates.append(f"{trigger}{item}")
                return candidates

        # Base commands
        for cmd in _DEFAULT_COMMANDS:
            clean_cmd = cmd.replace("ł", "l")
            if clean_cmd.startswith(prefix) or cmd.startswith(line_prefix):
                candidates.append(cmd)

        return sorted(set(candidates))


def setup_config_shell_readline(project_root: Path) -> Callable[[], None] | None:
    """Configure readline tab-completion and history file persistence.

    Returns a cleanup callable to save history upon session termination.
    """
    if readline is None:
        return None

    history_dir = project_root / ".koru"
    history_file = history_dir / "config_history"

    try:
        history_dir.mkdir(parents=True, exist_ok=True)
        if history_file.exists():
            readline.read_history_file(str(history_file))
    except Exception:
        pass

    completer = ConfigCompleter()
    readline.set_completer(completer.complete)
    readline.parse_and_bind("tab: complete")

    def _save_history() -> None:
        try:
            readline.write_history_file(str(history_file))
        except Exception:
            pass

    atexit.register(_save_history)
    return _save_history
