"""Optional ``llx`` bridge for dynamic decision-tree expansion.

When the user passes ``--llx`` to ``koru wizard``, we try to call the local
``llx`` CLI to produce additional options for the *current* node based on a
short summary of the project. The bridge is completely optional: if llx is not
installed, or fails, we silently keep the static tree.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from koru.wizard.tree import TreeNode, TreeOption

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LlxExpansion:
    """Result of asking llx for extra branches."""

    extra_options: tuple[TreeOption, ...]
    model: str
    raw_response: str


_PROMPT_TEMPLATE = (
    "Project root: {project}\n"
    "Current wizard node: {node_id} — \"{node_prompt}\"\n"
    "Existing options:\n{options}\n\n"
    "Suggest 1-3 ADDITIONAL strategic options (id, label) tailored to this\n"
    "specific project. Respond as STRICT JSON: {{\"options\": [{{\"id\":...,\n"
    "\"label\":...,\"ticket\":\"tpl_<existing>\"}}]}}. Use ONLY ticket ids from:\n"
    "{ticket_ids}"
)


def llx_available() -> bool:
    """True when the ``llx`` CLI is on PATH."""
    return shutil.which("llx") is not None


def _build_prompt(project: Path, node: TreeNode, ticket_ids: list[str]) -> str:
    options_block = "\n".join(f"  - {o.id}: {o.label}" for o in node.options) or "  (none)"
    return _PROMPT_TEMPLATE.format(
        project=str(project),
        node_id=node.id,
        node_prompt=node.prompt,
        options=options_block,
        ticket_ids=", ".join(ticket_ids),
    )


def _parse_llx_response(raw: str, ticket_ids: set[str]) -> tuple[TreeOption, ...]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.debug("llx returned non-JSON; ignoring")
        return ()
    options_raw = data.get("options") if isinstance(data, dict) else None
    if not isinstance(options_raw, list):
        return ()
    parsed: list[TreeOption] = []
    for entry in options_raw:
        if not isinstance(entry, dict):
            continue
        oid = str(entry.get("id") or "").strip()
        label = str(entry.get("label") or "").strip()
        ticket = str(entry.get("ticket") or "").strip()
        if not oid or not label:
            continue
        if ticket and ticket not in ticket_ids:
            ticket = ""
        parsed.append(
            TreeOption(
                id=f"llx_{oid}",
                label=f"[LLX] {label}",
                next_node=None,
                ticket=ticket or None,
            )
        )
    return tuple(parsed)


def expand_node(
    project: Path,
    node: TreeNode,
    *,
    ticket_ids: list[str],
    timeout: float = 25.0,
    runner: callable | None = None,
) -> LlxExpansion | None:
    """Ask ``llx chat`` for additional options for ``node``.

    Returns ``None`` when llx is unavailable, errors out, or returns no usable
    options. ``runner`` is a test hook: ``(argv, timeout) -> CompletedProcess``.
    """
    if not llx_available():
        return None

    prompt = _build_prompt(project, node, ticket_ids)
    argv = ["llx", "chat", "--prompt", prompt, "--format", "raw"]
    invoke = runner or (
        lambda cmd, t: subprocess.run(
            cmd, capture_output=True, text=True, timeout=t, check=False
        )
    )

    try:
        result = invoke(argv, timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.info("llx invocation failed: %s", exc)
        return None

    if getattr(result, "returncode", 1) != 0:
        logger.info("llx returned non-zero exit: %s", getattr(result, "stderr", ""))
        return None

    raw = (getattr(result, "stdout", "") or "").strip()
    extras = _parse_llx_response(raw, set(ticket_ids))
    if not extras:
        return None
    return LlxExpansion(extra_options=extras, model="llx-chat", raw_response=raw)
