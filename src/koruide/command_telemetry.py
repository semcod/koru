"""Per-command success telemetry for IDE drive integration."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_MAX_KEYS = 2000
_TELEMETRY_FILE = "command_telemetry.json"


def _telemetry_path(project: Path | None) -> Path | None:
    if project is None:
        return None
    return project / ".planfile" / ".koru" / _TELEMETRY_FILE


def _make_key(ide: str, plugin_version: str, capability: str, command: str) -> str:
    return f"{ide}|{plugin_version}|{capability}|{command}"


class CommandTelemetry:
    """Tracks attempts/ok per (ide, plugin_version, capability, command)."""

    def __init__(self, project: Path | None = None) -> None:
        self.project = project
        self._rows: dict[str, dict[str, Any]] = {}
        self._load()

    def record(
        self,
        *,
        ide: str,
        plugin_version: str,
        capability: str,
        command: str,
        ok: bool,
        reason: str = "",
        duration_ms: float | None = None,
    ) -> None:
        key = _make_key(ide, plugin_version, capability, command)
        row = self._rows.get(key)
        if row is None:
            row = {
                "ide": ide,
                "plugin_version": plugin_version,
                "capability": capability,
                "command": command,
                "attempts": 0,
                "ok": 0,
                "last_ok_at": None,
                "last_err": "",
                "p50_ms": None,
            }
            self._rows[key] = row
        row["attempts"] = int(row.get("attempts", 0)) + 1
        if ok:
            row["ok"] = int(row.get("ok", 0)) + 1
            row["last_ok_at"] = time.time()
        elif reason:
            row["last_err"] = reason[:200]
        if duration_ms is not None:
            prev = row.get("p50_ms")
            if prev is None:
                row["p50_ms"] = duration_ms
            else:
                row["p50_ms"] = (float(prev) + duration_ms) / 2.0
        self._trim()
        self._persist()

    def success_rate(self, ide: str, plugin_version: str, capability: str, command: str) -> float:
        key = _make_key(ide, plugin_version, capability, command)
        row = self._rows.get(key)
        if not row:
            return 0.0
        attempts = int(row.get("attempts", 0))
        if attempts <= 0:
            return 0.0
        return int(row.get("ok", 0)) / attempts

    def attempts(self, ide: str, plugin_version: str, capability: str, command: str) -> int:
        key = _make_key(ide, plugin_version, capability, command)
        row = self._rows.get(key)
        if not row:
            return 0
        return int(row.get("attempts", 0))

    def rows_for(
        self,
        ide: str,
        *,
        plugin_version: str | None = None,
        capability: str | None = None,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in self._rows.values():
            if row.get("ide") != ide:
                continue
            if plugin_version and row.get("plugin_version") != plugin_version:
                continue
            if capability and row.get("capability") != capability:
                continue
            attempts = int(row.get("attempts", 0))
            ok_count = int(row.get("ok", 0))
            enriched = dict(row)
            enriched["success_rate"] = (ok_count / attempts) if attempts else 0.0
            out.append(enriched)
        out.sort(
            key=lambda item: (
                -float(item.get("success_rate", 0)),
                -int(item.get("attempts", 0)),
            ),
        )
        return out

    def record_from_ack(
        self,
        *,
        ide: str,
        plugin_version: str | None,
        info: dict[str, Any],
    ) -> None:
        version = plugin_version or "unknown"
        trace = info.get("operation_trace")
        if isinstance(trace, list):
            for step in trace:
                if not isinstance(step, dict):
                    continue
                command = step.get("command")
                if not isinstance(command, str) or not command:
                    continue
                op = str(step.get("op") or "unknown")
                ok = step.get("ok") is True
                reason = str(step.get("reason") or "")
                self.record(
                    ide=ide,
                    plugin_version=version,
                    capability=op,
                    command=command,
                    ok=ok,
                    reason=reason,
                )
        for capability, field in (
            ("focus_open", "winning_focus_open"),
            ("paste", "winning_paste"),
            ("submit", "winning_submit"),
        ):
            command = info.get(field)
            if isinstance(command, str) and command:
                self.record(
                    ide=ide,
                    plugin_version=version,
                    capability=capability,
                    command=command,
                    ok=bool(info.get("ok", True)),
                    reason=str(info.get("submit_failure_reason") or ""),
                )

    def _trim(self) -> None:
        if len(self._rows) <= _MAX_KEYS:
            return
        ranked = sorted(
            self._rows.items(),
            key=lambda item: float(item[1].get("updated_at") or item[1].get("last_ok_at") or 0),
        )
        drop = len(self._rows) - _MAX_KEYS
        for key, _ in ranked[:drop]:
            del self._rows[key]

    def _persist(self) -> None:
        path = _telemetry_path(self.project)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "rows": list(self._rows.values())}
        try:
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        except OSError:
            return

    def _load(self) -> None:
        path = _telemetry_path(self.project)
        if path is None or not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        rows = data.get("rows") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            ide = row.get("ide")
            plugin_version = row.get("plugin_version")
            capability = row.get("capability")
            command = row.get("command")
            if not all(
                isinstance(value, str)
                for value in (ide, plugin_version, capability, command)
            ):
                continue
            key = _make_key(ide, plugin_version, capability, command)
            self._rows[key] = row


__all__ = ["CommandTelemetry"]
