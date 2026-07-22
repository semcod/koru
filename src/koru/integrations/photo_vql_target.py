"""Photo-VQL chat target selection — koru's binding to koruide's scorer.

The scoring heuristics moved to :mod:`koruide.chat_target` on 2026-07-22:
where JetBrains puts its composer, and how a VS Code-family top chat differs
from a status bar, is knowledge about IDEs — and koruide is the package that
owns IDE truth. Measured before moving: 31 of the 34 functions in the old file
touched no screen fact at all, only IDE layout. (The boundary proposal had
filed this file under "vdisplay owns screen truth"; that turned out to be the
wrong destination.)

Two things stayed here, because they describe *koru* rather than any IDE:

* the vocabularies that identify koru's own terminal output inside a capture
  (``KORU_``, ``DRY_RUN``, Polish operator prompts). They are registered into
  koruide at import time instead of being imported by it — koruide must not
  need to know what its host's console looks like;
* :func:`vql_candidates_polluted`, which answers "is this capture mostly my
  own terminal?" — a question only the host can ask.

Names are re-exported so existing call sites, and the tests that monkeypatch
them, keep working.
"""

from __future__ import annotations

from typing import Any

from koruide.chat_target import (
    VSCODE_FAMILY_TOP_CHAT_IDES,
    jetbrains_chat_corner_target_from_layers,
    jetbrains_chat_target_from_surface,
    jetbrains_corner_rejected,
    photo_vql_chat_input_candidates,
    score_photo_vql_chat_input,
    set_label_noise_tokens,
    vql_layers_show_vdisplay_overlay,
    vscode_family_chat_target_from_layers,
    vscode_family_top_chat_rejected,
)

from koru.integrations.photo_vql_validation import (
    SHELL_POLLUTION_TOKENS,
    VQL_TERMINAL_LABEL_NOISE,
)

# Hand koruide koru's own noise vocabulary. Without this the penalties stay at
# zero and koru's console can outscore a real chat input.
set_label_noise_tokens(
    label_noise=VQL_TERMINAL_LABEL_NOISE,
    shell_pollution=SHELL_POLLUTION_TOKENS,
)


def _has_any(text: str, tokens: tuple[str, ...] | list[str]) -> bool:
    return any(token.lower() in text for token in tokens)


def vql_candidates_polluted(candidates: list[dict[str, Any]]) -> bool:
    """True when at least half the candidates look like koru's own console."""
    polluted_count = 0
    for candidate in candidates:
        label = str(candidate.get("label") or "").lower()
        if _has_any(label, SHELL_POLLUTION_TOKENS):
            polluted_count += 1
    return len(candidates) > 0 and polluted_count >= max(1, len(candidates) // 2)


__all__ = [
    "VSCODE_FAMILY_TOP_CHAT_IDES",
    "jetbrains_chat_corner_target_from_layers",
    "jetbrains_chat_target_from_surface",
    "jetbrains_corner_rejected",
    "photo_vql_chat_input_candidates",
    "score_photo_vql_chat_input",
    "vql_candidates_polluted",
    "vql_layers_show_vdisplay_overlay",
    "vscode_family_chat_target_from_layers",
    "vscode_family_top_chat_rejected",
]
