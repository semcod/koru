"""Pick ordered IDE commands for drive phases (heuristic + optional OpenRouter)."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

from koru.autonomy_strategy.openrouter import call_openrouter_json
from koruide.command_catalog import GENERIC_VSCODE_FAMILY, IDE_ROWS
from koruide.command_telemetry import CommandTelemetry

_LADDER_SEED: dict[str, list[str]] = {}


def _seed_append(category: str, command_id: str) -> None:
    bucket = _LADDER_SEED.setdefault(category, [])
    if command_id not in bucket:
        bucket.append(command_id)


for _row in GENERIC_VSCODE_FAMILY:
    _seed_append(_row.category, _row.id)

for _rows in IDE_ROWS.values():
    for _row in _rows:
        _seed_append(_row.category, _row.id)

_LLM_CACHE: dict[str, tuple[float, list[str]]] = {}
_LLM_CACHE_TTL_SECONDS = 24 * 3600
_VSCODIUM_FOCUS_OPEN_AVOID = (
    "openquickchat",
    "quickchat.openinchatview",
    "action.openchat",
    "action.openchatview",
    "action.chat.open",
    "settings",
    "preferences",
    "openagent",
    "openask",
    "focusinput",
)
_VSCODIUM_FOCUS_OPEN_PREFERRED = (
    "chatgpt.sidebarView.open",
    "chatgpt.openSidebar",
    "chatgpt.sidebarSecondaryView.open",
    "workbench.action.chat.openInSidebar",
    "workbench.panel.chat",
    "workbench.panel.chat.view.copilot.focus",
)
_CURSOR_SUBMIT_EXACT_ALLOW = {
    "workbench.action.chat.submit",
    "workbench.action.chat.acceptInput",
    "workbench.action.chat.send",
    "workbench.action.chat.sendMessage",
    "workbench.action.chat.stopListeningAndSubmit",
}
_CURSOR_SUBMIT_PREFIX_ALLOW = (
    "composer.",
    "aichat.",
)
_CURSOR_FAST_PATH_ONLY = (
    "composer.startComposerPrompt",
    "composer.startComposerPrompt2",
)
_CURSOR_PASTE_REJECT = {
    "editor.action.clipboardPasteAction",
    "editor.action.pasteAs",
    "execPaste",
    "paste",
    "workbench.action.terminal.paste",
}
_CURSOR_FOCUS_OPEN_REJECT = {
    "workbench.panel.chat",
    "composer.openaspane",
    "aichat.newchataction",
    "workbench.action.toggleauxiliarybar",
    "workbench.view.chat.toggle",
}
_TRUE_ENV_VALUES = {"1", "true", "yes", "on"}


def _llm_picker_mode() -> str:
    return os.environ.get("KORU_LLM_PICKER", "auto").strip().lower()


def _seed_order(capability: str) -> dict[str, int]:
    seed = _LADDER_SEED.get(capability, ())
    return {command: index for index, command in enumerate(seed)}


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUE_ENV_VALUES


def _sanitize_antigravity_focus_open(commands: list[str]) -> list[str]:
    return [cmd for cmd in commands if cmd != "aichat.newchataction"]


def _is_vscodium_focus_open_candidate(command: str) -> bool:
    lowered = command.lower()
    return not any(marker in lowered for marker in _VSCODIUM_FOCUS_OPEN_AVOID)


def _prefer_commands(commands: list[str], preferred: tuple[str, ...]) -> list[str]:
    ordered = [command for command in preferred if command in commands]
    ordered.extend(command for command in commands if command not in ordered)
    return ordered


def _sanitize_vscodium_focus_open(commands: list[str]) -> list[str]:
    if not _env_enabled("KORU_VSCODIUM_COMMAND_ORDER_FOCUS_OPEN"):
        return []
    filtered = [command for command in commands if _is_vscodium_focus_open_candidate(command)]
    return _prefer_commands(filtered, _VSCODIUM_FOCUS_OPEN_PREFERRED)


def _is_cursor_submit_candidate(command: str) -> bool:
    if command in _CURSOR_FAST_PATH_ONLY:
        return False
    return command in _CURSOR_SUBMIT_EXACT_ALLOW or command.startswith(
        _CURSOR_SUBMIT_PREFIX_ALLOW,
    )


def _sanitize_cursor_submit(commands: list[str]) -> list[str]:
    filtered = [command for command in commands if _is_cursor_submit_candidate(command)]
    if filtered:
        return filtered
    return ["composer.sendToAgent", "workbench.action.chat.submit"]


def _is_cursor_paste_candidate(command: str) -> bool:
    if command in _CURSOR_FAST_PATH_ONLY:
        return False
    return command not in _CURSOR_PASTE_REJECT


def _sanitize_cursor_paste(commands: list[str]) -> list[str]:
    filtered = [command for command in commands if _is_cursor_paste_candidate(command)]
    if filtered:
        return filtered
    return [
        "workbench.action.chat.typeText",
        "workbench.action.chat.insertText",
        "cursor.action.chat.typeText",
        "composer.typeText",
    ]


def _is_cursor_focus_open_candidate(command: str) -> bool:
    return command.strip().lower() not in _CURSOR_FOCUS_OPEN_REJECT


def _sanitize_cursor_focus_open(commands: list[str]) -> list[str]:
    filtered = [command for command in commands if _is_cursor_focus_open_candidate(command)]
    if filtered:
        return filtered
    return [
        "workbench.action.chat.open",
        "workbench.action.chat.openagent",
        "workbench.action.openChat",
        "workbench.panel.chat.view.copilot.focus",
    ]


def _sanitize_focus_open_candidates(ide_id: str, commands: list[str]) -> list[str]:
    if ide_id == "antigravity":
        return _sanitize_antigravity_focus_open(commands)
    if ide_id == "vscodium":
        return _sanitize_vscodium_focus_open(commands)
    if ide_id == "cursor":
        return _sanitize_cursor_focus_open(commands)
    return commands


def _sanitize_cursor_candidates(capability: str, commands: list[str]) -> list[str]:
    if capability == "submit":
        return _sanitize_cursor_submit(commands)
    if capability == "paste":
        return _sanitize_cursor_paste(commands)
    return commands


def _sanitize_candidates(ide: str, capability: str, commands: list[str]) -> list[str]:
    ide_id = ide.strip().lower()
    if capability == "focus_open":
        return _sanitize_focus_open_candidates(ide_id, commands)
    if ide_id == "cursor":
        return _sanitize_cursor_candidates(capability, commands)

    return commands


def _reorder_cursor_submit_default(commands: list[str]) -> list[str]:
    def rank(command: str) -> tuple[int, int]:
        if command == "workbench.action.chat.stopListeningAndSubmit":
            return 0, 0
        if command in _CURSOR_SUBMIT_EXACT_ALLOW:
            return 1, 0
        if command.startswith(("composer.", "aichat.")):
            return 2, 0
        return 3, 0

    return sorted(commands, key=rank)


def _reorder_submit_for_hint(
    ide: str,
    commands: list[str],
    hint: str | None,
) -> list[str]:
    if not hint or ide.strip().lower() != "cursor":
        return commands
    normalized = hint.strip().lower()
    if normalized == "submit_alt_glass_first":

        def sort_key(command: str) -> tuple[int, int]:
            if command.startswith(("composer.", "aichat.")):
                return 0, 0
            if command in _CURSOR_SUBMIT_EXACT_ALLOW:
                return 1, 0
            return 2, 0

    elif normalized == "submit_alt_registered":

        def sort_key(command: str) -> tuple[int, int]:
            if command in _CURSOR_SUBMIT_EXACT_ALLOW:
                return 0, 0
            if command.startswith(("composer.", "aichat.")):
                return 1, 0
            return 2, 0

    else:
        return commands
    return sorted(commands, key=sort_key)


@dataclass
class HeuristicPicker:
    telemetry: CommandTelemetry | None = None

    def pick(
        self,
        ide: str,
        capability: str,
        *,
        catalog: dict[str, list[str]] | None,
        plugin_version: str | None = None,
        recent_dsl: list[str] | None = None,
        hint: str | None = None,
        limit: int = 12,
    ) -> list[str]:
        del recent_dsl
        candidates = list((catalog or {}).get(capability) or [])
        if not candidates:
            candidates = list(_LADDER_SEED.get(capability, ()))
        candidates = _sanitize_candidates(ide, capability, candidates)
        version = plugin_version or "unknown"
        seed_rank = _seed_order(capability)

        def sort_key(command: str) -> tuple[float, float, int]:
            rate = 0.0
            attempts = 0
            if self.telemetry is not None:
                rate = self.telemetry.success_rate(ide, version, capability, command)
                attempts = self.telemetry.attempts(ide, version, capability, command)
            return (-rate, -float(attempts), seed_rank.get(command, 9999))

        ordered = sorted(candidates, key=sort_key)
        if capability == "submit" and ide.strip().lower() == "cursor":
            ordered = _reorder_cursor_submit_default(ordered)
        if capability == "submit" and hint:
            ordered = _reorder_submit_for_hint(ide, ordered, hint)
        return ordered[:limit]


@dataclass
class OpenRouterPicker:
    heuristic: HeuristicPicker = field(default_factory=HeuristicPicker)
    timeout_seconds: float = 5.0
    model: str = "qwen/qwen3-coder-next"

    def pick(
        self,
        ide: str,
        capability: str,
        *,
        catalog: dict[str, list[str]] | None,
        plugin_version: str | None = None,
        recent_dsl: list[str] | None = None,
        hint: str | None = None,
        limit: int = 12,
    ) -> list[str]:
        version = plugin_version or "unknown"
        if not self._should_call_llm(ide, version, capability, hint=hint):
            return self.heuristic.pick(
                ide,
                capability,
                catalog=catalog,
                plugin_version=plugin_version,
                recent_dsl=recent_dsl,
                hint=hint,
                limit=limit,
            )
        cache_key = f"{ide}|{version}|{capability}"
        cached = _LLM_CACHE.get(cache_key)
        if cached and time.time() - cached[0] < _LLM_CACHE_TTL_SECONDS:
            return cached[1][:limit]
        ordered = self._call_llm(
            ide,
            capability,
            catalog=catalog,
            plugin_version=version,
            recent_dsl=recent_dsl or [],
            limit=limit,
        )
        if ordered:
            _LLM_CACHE[cache_key] = (time.time(), ordered)
            return ordered[:limit]
        return self.heuristic.pick(
            ide,
            capability,
            catalog=catalog,
            plugin_version=plugin_version,
            recent_dsl=recent_dsl,
            hint=hint,
            limit=limit,
        )

    def _should_call_llm(
        self,
        ide: str,
        plugin_version: str,
        capability: str,
        *,
        hint: str | None,
    ) -> bool:
        mode = _llm_picker_mode()
        if mode in {"always", "1", "true", "yes", "on"}:
            return True
        if hint and hint.strip().lower() in {"llm", "openrouter"}:
            return True
        if mode in {"never", "0", "false", "no", "off"}:
            return False
        telemetry = self.heuristic.telemetry
        if telemetry is None:
            return False
        cap_rows = telemetry.rows_for(ide, plugin_version=plugin_version, capability=capability)
        total_attempts = sum(int(row.get("attempts", 0)) for row in cap_rows)
        if total_attempts < 3:
            return True
        heuristic = self.heuristic.pick(
            ide,
            capability,
            catalog=None,
            plugin_version=plugin_version,
            limit=1,
        )
        if not heuristic:
            return total_attempts < 3
        top = heuristic[0]
        rate = telemetry.success_rate(ide, plugin_version, capability, top)
        recent_attempts = telemetry.attempts(ide, plugin_version, capability, top)
        return recent_attempts >= 10 and rate < 0.5

    def _call_llm(
        self,
        ide: str,
        capability: str,
        *,
        catalog: dict[str, list[str]] | None,
        plugin_version: str,
        recent_dsl: list[str],
        limit: int,
    ) -> list[str]:
        candidates = list((catalog or {}).get(capability) or [])
        if not candidates:
            return []
        telemetry = self.heuristic.telemetry
        lines = [
            f"IDE: {ide} (plugin {plugin_version})",
            f"Capability: {capability}",
            "Candidates:",
        ]
        for command in candidates[:40]:
            rate = 0.0
            attempts = 0
            if telemetry is not None:
                rate = telemetry.success_rate(ide, plugin_version, capability, command)
                attempts = telemetry.attempts(ide, plugin_version, capability, command)
            lines.append(f"  {command} ok={int(rate * attempts)}/{attempts}")
        if recent_dsl:
            lines.append("Last DSL trace:")
            lines.extend(f"  {line}" for line in recent_dsl[-8:])
        lines.append(
            f'Pick up to {limit} command ids in order. Return JSON only: '
            '{"ordered":["cmd1","cmd2"],"why":"short reason"}'
        )
        response = call_openrouter_json(
            "\n".join(lines),
            system_prompt="Return only valid JSON with keys ordered and why.",
            timeout_seconds=self.timeout_seconds,
            model=self.model,
        )
        if not response.ok:
            return []
        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError:
            return []
        ordered_raw = payload.get("ordered")
        if not isinstance(ordered_raw, list):
            return []
        existing = set(candidates)
        ordered = [item for item in ordered_raw if isinstance(item, str) and item in existing]
        return ordered


def build_command_picker(telemetry: CommandTelemetry | None) -> OpenRouterPicker | HeuristicPicker:
    heuristic = HeuristicPicker(telemetry=telemetry)
    mode = _llm_picker_mode()
    if mode in {"never", "0", "false", "no", "off", "heuristic"}:
        return heuristic
    if mode in {"heuristic-only"}:
        return heuristic
    return OpenRouterPicker(heuristic=heuristic)


def pick_command_order(
    *,
    ide: str,
    plugin_version: str | None,
    catalog: dict[str, list[str]] | None,
    telemetry: CommandTelemetry | None,
    recent_dsl: list[str] | None = None,
    strategy_hint: str | None = None,
) -> dict[str, list[str]]:
    """Return per-capability command order for a drive envelope."""
    picker = build_command_picker(telemetry)
    order: dict[str, list[str]] = {}
    for capability in ("focus_open", "focus_input", "paste", "submit"):
        picked = picker.pick(
            ide,
            capability,
            catalog=catalog,
            plugin_version=plugin_version,
            recent_dsl=recent_dsl,
            hint=strategy_hint,
        )
        if picked:
            order[capability] = picked
    return order


__all__ = [
    "HeuristicPicker",
    "OpenRouterPicker",
    "build_command_picker",
    "pick_command_order",
]
