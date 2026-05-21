"""Small decision helpers for autopilot drive / ack flow."""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Any

from koruide.plugin_version import EXPECTED_VSCODE_PLUGIN_VERSION


class DriveOrchestrator:
    """Pure helpers used by the autopilot daemon."""

    @staticmethod
    def plugin_required_message(ide: str | None) -> str:
        label = ide or "auto"
        return (
            f"no connected autopilot plugin for ide={label}; "
            "keyboard fallback disabled for this request. "
            "Reload the IDE window or run the `koru: Connect autopilot daemon` command "
            "so the extension connects to this socket."
        )

    @staticmethod
    def should_try_os_fallback(
        *,
        plugin_ok: bool,
        info: dict[str, Any],
        submit_requested: bool,
        plugin_ide: str | None,
        require_plugin: bool,
    ) -> bool:
        if require_plugin or not plugin_ide:
            return False
        focus_error = "chat input is not focused/open" in str(info.get("message", "")).lower()
        submit_failed = submit_requested and info.get("submitted") is False
        undelivered = info.get("delivered") is False
        return ((not plugin_ok) and focus_error) or (not plugin_ok) or submit_failed or undelivered

    @staticmethod
    def build_message_sent_info(
        *,
        submit_requested: bool,
        plugin_ide: str | None,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        info: dict[str, Any] = {
            "backend": "plugin",
            "delivered": True,
            "opened": True,
            "submitted": submit_requested,
            "event": "message.sent",
        }
        if plugin_ide:
            info["ide"] = plugin_ide
        if isinstance(event_data.get("chat"), str):
            info["chat"] = event_data["chat"]
        info["verification"] = "event_only"
        return info

    @staticmethod
    def annotate_plugin_ack(
        *,
        info: dict[str, Any],
        plugin_ok: bool,
        submit_requested: bool,
    ) -> dict[str, Any]:
        enriched = dict(info)
        if not plugin_ok:
            enriched.setdefault("verification", "plugin_error")
            return enriched
        if enriched.get("event") == "message.sent":
            enriched["verification"] = "event_only"
            return enriched
        if submit_requested:
            has_submit_proof = bool(enriched.get("winning_submit"))
            has_paste_proof = bool(enriched.get("winning_paste"))
            has_open_proof = bool(enriched.get("winning_focus_open"))
            if has_submit_proof and has_paste_proof and has_open_proof:
                enriched["verification"] = "strict"
            else:
                enriched["verification"] = "plugin_ack"
        else:
            enriched.setdefault("verification", "plugin_ack")
        return enriched

    @staticmethod
    def strict_plugin_ack_required() -> bool:
        raw = os.environ.get("KORU_STRICT_PLUGIN_ACK", "").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def expected_plugin_version() -> str | None:
        here = Path(__file__).resolve()
        for parent in here.parents:
            package_json = parent / "plugins" / "koru-autopilot-vscode" / "package.json"
            if not package_json.is_file():
                continue
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
            version = data.get("version")
            return str(version) if version else None
        return EXPECTED_VSCODE_PLUGIN_VERSION

    @staticmethod
    def strict_plugin_version_required() -> bool:
        raw = os.environ.get("KORU_STRICT_PLUGIN_VERSION", "").strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
        policy = os.environ.get("KORU_PLUGIN_VERSION_POLICY", "").strip().lower()
        return policy in {"strict", "fail", "fail-fast", "block"}

    @staticmethod
    def plugin_version_info(
        *,
        plugin_ide: str | None,
        connected_version: str | None,
        expected_version: str | None = None,
    ) -> dict[str, Any]:
        expected = expected_version or DriveOrchestrator.expected_plugin_version()
        strict = DriveOrchestrator.strict_plugin_version_required()
        mismatch = bool(connected_version and expected and connected_version != expected)
        unknown_expected = bool(strict and connected_version and not expected)
        info: dict[str, Any] = {
            "plugin_version": connected_version,
            "expected_plugin_version": expected,
            "plugin_version_mismatch": mismatch,
            "plugin_version_expected_missing": unknown_expected,
            "plugin_version_policy": (
                "strict" if strict else "warn"
            ),
        }
        if plugin_ide:
            info["ide"] = plugin_ide
        return info

    @staticmethod
    def should_block_plugin_version(info: dict[str, Any]) -> bool:
        return bool(
            info.get("plugin_version_mismatch")
            or info.get("plugin_version_expected_missing"),
        ) and DriveOrchestrator.strict_plugin_version_required()

    @staticmethod
    def plugin_version_block_message(info: dict[str, Any]) -> str:
        return (
            "connected autopilot plugin version mismatch: "
            f"connected={info.get('plugin_version') or '-'} "
            f"expected={info.get('expected_plugin_version') or '-'}; "
            "reload the IDE window after installing the current VSIX, then run "
            "`koru: Connect autopilot daemon`."
        )

    @staticmethod
    def should_fail_strict_plugin_ack(
        *,
        info: dict[str, Any],
        plugin_ok: bool,
        submit_requested: bool,
        plugin_ide: str | None,
    ) -> bool:
        if not DriveOrchestrator.strict_plugin_ack_required():
            return False
        if not plugin_ok or not submit_requested:
            return False
        if (plugin_ide or "").lower() != "vscode":
            return False
        return str(info.get("verification", "")) != "strict"

    @staticmethod
    def plugin_ack_summary(info: dict[str, Any]) -> str:
        parts: list[str] = []
        verification = info.get("verification")
        if verification:
            parts.append(f"verification={verification}")
        for key in ("winning_focus_open", "winning_paste", "winning_submit"):
            value = info.get(key)
            if value:
                parts.append(f"{key}={value}")
        if info.get("plugin_version_mismatch"):
            parts.append(
                "plugin_version="
                f"{info.get('plugin_version') or '-'}"
                f"/expected={info.get('expected_plugin_version') or '-'}"
            )
        if info.get("event"):
            parts.append(f"event={info['event']}")
        return " ".join(parts)


__all__ = ["DriveOrchestrator"]
