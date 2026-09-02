"""Append-only event store for dsl2koru commands (protobuf + jsonl)."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from dsl2koru.pb_codec import encode_protobuf, envelope_to_dict, pb_to_result, result_to_pb
from dsl2koru.result import DslResult
from dsl2koru.v1 import result_pb2

StoreFormat = Literal["protobuf", "jsonl"]


@dataclass(frozen=True)
class StoredEvent:
    id: str
    ts_unix: int
    command: dict[str, Any]
    result: dict[str, Any]
    correlation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventStore:
    def __init__(self, path: Path, *, fmt: StoreFormat | None = None) -> None:
        self.path = path
        if fmt is not None:
            self.fmt = fmt
        elif self.path.suffix == ".pb":
            self.fmt = "protobuf"
        else:
            self.fmt = "jsonl"

    @classmethod
    def _for_root(cls, root: Path, namespace: str, prefer_pb: bool) -> EventStore:
        events_dir = root.expanduser().resolve() / namespace / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        fmt: StoreFormat = "protobuf" if prefer_pb else "jsonl"
        return cls(events_dir / f"dsl.events.{('pb' if prefer_pb else 'jsonl')}", fmt=fmt)

    @classmethod
    def for_project(cls, project_root: Path, *, prefer_pb: bool = True) -> EventStore:
        return cls._for_root(project_root, ".koru", prefer_pb)

    @classmethod
    def for_default(cls, default_file: str | None = None, *, prefer_pb: bool = True) -> EventStore:
        """Build the one-release Coru-compatible event-store location."""
        root = Path(default_file or ".").expanduser().resolve().parent
        return cls._for_root(root, ".coru", prefer_pb)

    def append_command(self, command: dict[str, Any], result: dict[str, Any], *, correlation_id: str = "") -> str:
        event_id = uuid.uuid4().hex
        event = StoredEvent(
            id=event_id,
            ts_unix=int(time.time()),
            command=command,
            result=result,
            correlation_id=correlation_id,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.fmt == "protobuf":
            pb = result_pb2.DslEvent()
            pb.id = event.id
            pb.ts_unix = event.ts_unix
            pb.correlation_id = correlation_id
            pb.command.ParseFromString(encode_protobuf(command, correlation_id=correlation_id))
            dsl_result = DslResult(
                ok=bool(result.get("ok")),
                verb=str(result.get("verb", command.get("verb", ""))),
                command=str(result.get("command", "")),
                action=str(result.get("action", "")),
                output=str(result.get("output", "")),
                data=dict(result.get("data") or {}),
                error=result.get("error"),
                event_id=event_id,
            )
            pb.result.CopyFrom(result_to_pb(dsl_result))
            data = pb.SerializeToString()
            with self.path.open("ab") as fh:
                fh.write(len(data).to_bytes(4, "big"))
                fh.write(data)
        else:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        return event_id

    @staticmethod
    def _read_protobuf(path: Path) -> list[StoredEvent]:
        events: list[StoredEvent] = []
        data = path.read_bytes()
        offset = 0
        while offset + 4 <= len(data):
            size = int.from_bytes(data[offset : offset + 4], "big")
            offset += 4
            pb = result_pb2.DslEvent()
            pb.ParseFromString(data[offset : offset + size])
            offset += size
            events.append(
                StoredEvent(
                    id=pb.id,
                    ts_unix=int(pb.ts_unix),
                    command=envelope_to_dict(pb.command),
                    result=pb_to_result(pb.result).to_dict(),
                    correlation_id=pb.correlation_id,
                ),
            )
        return events

    def read_all(self) -> list[StoredEvent]:
        if not self.path.is_file():
            return []
        if self.fmt == "protobuf":
            return self._read_protobuf(self.path)
        events = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            events.append(
                StoredEvent(
                    id=str(data["id"]),
                    ts_unix=int(data["ts_unix"]),
                    command=dict(data["command"]),
                    result=dict(data["result"]),
                    correlation_id=str(data.get("correlation_id", "")),
                ),
            )
        return events

    def replay_pb(self) -> list[StoredEvent]:
        pb_path = self.path if self.path.suffix == ".pb" else self.path.with_suffix(".pb")
        return self._read_protobuf(pb_path) if pb_path.is_file() else []

    def replay(self, *, prefer_pb: bool = True) -> list[StoredEvent]:
        if prefer_pb and self.fmt == "protobuf":
            pb_events = self.replay_pb()
            if pb_events:
                return pb_events
        return self.read_all()
