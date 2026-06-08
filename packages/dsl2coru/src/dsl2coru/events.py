"""Append-only event store for dsl2coru commands."""

from __future__ import annotations

import base64
import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from dsl2coru.result import DslResult

StoreFormat = Literal["protobuf", "jsonl"]


@dataclass
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
            self.fmt: StoreFormat = fmt
        elif self.path.suffix == ".pb":
            self.fmt = "protobuf"
        else:
            self.fmt = "jsonl"

    @classmethod
    def for_default(cls, default_file: str | None = None, *, prefer_pb: bool = True) -> EventStore:
        root = Path(default_file or ".").expanduser().resolve().parent
        events_dir = root / ".coru" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        if prefer_pb:
            return cls(events_dir / "dsl.events.pb", fmt="protobuf")
        return cls(events_dir / "dsl.events.jsonl", fmt="jsonl")

    def append_command(self, command: dict[str, Any], result: dict[str, Any], *, correlation_id: str = "") -> str:
        event_id = uuid.uuid4().hex
        record = StoredEvent(
            id=event_id,
            ts_unix=int(time.time()),
            command=command,
            result=result,
            correlation_id=correlation_id,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.fmt == "protobuf":
            self._append_pb(record)
        else:
            self._append_jsonl(record)
        return event_id

    def _append_pb(self, event: StoredEvent) -> None:
        from dsl2coru.pb_codec import dict_to_envelope, result_to_pb
        from dsl2coru.v1 import result_pb2

        pb = result_pb2.DslEvent()
        pb.id = event.id
        pb.ts_unix = event.ts_unix
        pb.correlation_id = event.correlation_id
        pb.command.CopyFrom(dict_to_envelope(event.command, correlation_id=event.correlation_id))
        dsl_result = DslResult(
            ok=bool(event.result.get("ok")),
            verb=str(event.result.get("verb", "")),
            command=str(event.result.get("command", "")),
            action=str(event.result.get("action", "")),
            output=str(event.result.get("output", "")),
            data=dict(event.result.get("data") or {}),
            error=event.result.get("error"),
            event_id=event.id,
        )
        pb.result.CopyFrom(result_to_pb(dsl_result))
        data = pb.SerializeToString()
        pb_path = self.path if self.path.suffix == ".pb" else self.path.with_suffix(".pb")
        with pb_path.open("ab") as fh:
            fh.write(len(data).to_bytes(4, "big"))
            fh.write(data)

    def _append_jsonl(self, event: StoredEvent) -> None:
        row = event.to_dict()
        try:
            from dsl2coru.pb_codec import dict_to_envelope, result_to_pb
            from dsl2coru.v1 import result_pb2

            pb_event = result_pb2.DslEvent()
            pb_event.id = event.id
            pb_event.ts_unix = event.ts_unix
            pb_event.correlation_id = event.correlation_id
            pb_event.command.CopyFrom(dict_to_envelope(event.command, correlation_id=event.correlation_id))
            dsl_result = DslResult(
                ok=bool(event.result.get("ok")),
                verb=str(event.result.get("verb", "")),
                command=str(event.result.get("command", "")),
                action=str(event.result.get("action", "")),
                output=str(event.result.get("output", "")),
                data=dict(event.result.get("data") or {}),
                error=event.result.get("error"),
                event_id=event.id,
            )
            pb_event.result.CopyFrom(result_to_pb(dsl_result))
            row["pb"] = base64.b64encode(pb_event.SerializeToString()).decode("ascii")
        except Exception:
            pass
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def read_all(self) -> list[StoredEvent]:
        if not self.path.is_file():
            return []
        events: list[StoredEvent] = []
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
        if not pb_path.is_file():
            return []
        from dsl2coru.pb_codec import envelope_to_dict, pb_to_result
        from dsl2coru.v1 import result_pb2

        events: list[StoredEvent] = []
        data = pb_path.read_bytes()
        offset = 0
        while offset + 4 <= len(data):
            size = int.from_bytes(data[offset : offset + 4], "big")
            offset += 4
            chunk = data[offset : offset + size]
            offset += size
            pb = result_pb2.DslEvent()
            pb.ParseFromString(chunk)
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

    def replay(self, *, prefer_pb: bool = True) -> list[StoredEvent]:
        if prefer_pb:
            pb_events = self.replay_pb()
            if pb_events:
                return pb_events
        return self.read_all()
