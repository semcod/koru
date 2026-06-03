"""Lane registry data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LaneHealth:
    daemon_running: bool = False
    plugin_connected: bool = False
    plugin_count: int = 0
    daemon_version: str | None = None
    plugin_version: str | None = None
    plugin_build: str | None = None
    expected_build: str | None = None
    issues: list[str] = field(default_factory=list)
    checked_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LaneRecord:
    ide: str
    instance: str
    socket_path: str
    editor_cli: str | None = None
    project: str | None = None
    daemon_desired: bool = True
    health: LaneHealth = field(default_factory=LaneHealth)
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["health"] = self.health.to_dict()
        return payload

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> LaneRecord:
        health_raw = raw.get("health") if isinstance(raw.get("health"), dict) else {}
        health = LaneHealth(
            daemon_running=bool(health_raw.get("daemon_running", False)),
            plugin_connected=bool(health_raw.get("plugin_connected", False)),
            plugin_count=int(health_raw.get("plugin_count") or 0),
            daemon_version=health_raw.get("daemon_version"),
            plugin_version=health_raw.get("plugin_version"),
            plugin_build=health_raw.get("plugin_build"),
            expected_build=health_raw.get("expected_build"),
            issues=[str(x) for x in health_raw.get("issues") or []],
            checked_at=health_raw.get("checked_at"),
        )
        return cls(
            ide=str(raw.get("ide") or ""),
            instance=str(raw.get("instance") or ""),
            socket_path=str(raw.get("socket_path") or ""),
            editor_cli=raw.get("editor_cli"),
            project=raw.get("project"),
            daemon_desired=bool(raw.get("daemon_desired", True)),
            health=health,
            created_at=raw.get("created_at"),
            updated_at=raw.get("updated_at"),
        )


@dataclass
class SupervisorRegistry:
    version: int = 1
    active_lane: str | None = None
    lanes: dict[str, LaneRecord] = field(default_factory=dict)
    http_host: str = "127.0.0.1"
    http_port: int = 8766
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "active_lane": self.active_lane,
            "lanes": {key: lane.to_dict() for key, lane in self.lanes.items()},
            "http_host": self.http_host,
            "http_port": self.http_port,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SupervisorRegistry:
        lanes_raw = raw.get("lanes") if isinstance(raw.get("lanes"), dict) else {}
        lanes = {
            str(key): LaneRecord.from_dict(value)
            for key, value in lanes_raw.items()
            if isinstance(value, dict)
        }
        return cls(
            version=int(raw.get("version") or 1),
            active_lane=raw.get("active_lane"),
            lanes=lanes,
            http_host=str(raw.get("http_host") or "127.0.0.1"),
            http_port=int(raw.get("http_port") or 8766),
            updated_at=raw.get("updated_at"),
        )

    def active_record(self) -> LaneRecord | None:
        if not self.active_lane:
            return None
        return self.lanes.get(self.active_lane)
