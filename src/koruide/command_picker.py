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
    "panel.chat",
    "openagent",
    "openask",
)
_VSCODIUM_FOCUS_OPEN_PREFERRED = (
    "workbench.action.chat.focusInput",
)


def _llm_picker_mode() -> str:
    return os.environ.get("KORU_LLM_PICKER", "auto").strip().lower()


def _seed_order(capability: str) -> dict[str, int]:
    seed = _LADDER_SEED.get(capability, ())
    return {command: index for index, command in enumerate(seed)}


def _sanitize_candidates(ide: str, capability: str, commands: list[str]) -> list[str]:
    if ide.strip().lower() != "vscodium" or capability != "focus_open":
        return commands
    if os.environ.get("KORU_VSCODIUM_COMMAND_ORDER_FOCUS_OPEN", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return []
    filtered = [
        command
        for command in commands
        if not any(marker in command.lower() for marker in _VSCODIUM_FOCUS_OPEN_AVOID)
    ]
    # VSCodium has a strategy-level focusInput-only opener. Re-add it when the
    # live catalog only exposes high-risk open/new-chat commands.
    ordered = [command for command in _VSCODIUM_FOCUS_OPEN_PREFERRED if command in filtered]
    ordered.extend(command for command in filtered if command not in ordered)
    if not ordered:
        ordered = list(_VSCODIUM_FOCUS_OPEN_PREFERRED)
    return ordered


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
        del recent_dsl, hint
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
