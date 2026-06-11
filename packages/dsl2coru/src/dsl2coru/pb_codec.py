"""Dict ↔ protobuf DslEnvelope / DslResult."""

from __future__ import annotations

import json
from typing import Any

from dsl2coru.grammar import parse_line, to_text
from dsl2coru.result import DslResult
from dsl2coru.v1 import command_pb2, result_pb2

_BODY_MAP = {
    "STATUS": "status",
    "REPAIR_HISTORY": "repair_history",
    "ENV": "env",
    "QUERY": "query",
    "AUTO": "auto",
    "LANE": "lane",
    "ENSURE": "ensure",
    "DOCTOR": "doctor",
    "CALIBRATION": "calibration",
    "CHAT": "chat",
    "TEXT": "text",
    "SYNC": "sync",
    "REPAIR_RUN": "repair_run",
}


def _set_status(msg: Any, cmd: dict[str, Any]) -> None:
    msg.probe = bool(cmd.get("probe"))


def _set_env(msg: Any, cmd: dict[str, Any]) -> None:
    if cmd.get("file"):
        msg.file = str(cmd["file"])


def _set_query(msg: Any, cmd: dict[str, Any]) -> None:
    if cmd.get("target"):
        msg.target = str(cmd["target"])


def _set_auto(msg: Any, cmd: dict[str, Any]) -> None:
    if cmd.get("shell"):
        msg.shell = str(cmd["shell"])
    if args := cmd.get("auto_args"):
        if isinstance(args, str):
            msg.auto_args.extend(args.split())
        else:
            msg.auto_args.extend([str(item) for item in args])
    if cmd.get("target"):
        msg.target = str(cmd["target"])


def _set_lane(msg: Any, cmd: dict[str, Any]) -> None:
    if cmd.get("ide"):
        msg.ide = str(cmd["ide"])
    if cmd.get("instance"):
        msg.instance = str(cmd["instance"])
    if cmd.get("file"):
        msg.file = str(cmd["file"])
    msg.lane_status = bool(cmd.get("lane_status"))


def _set_ensure(msg: Any, cmd: dict[str, Any]) -> None:
    msg.install = bool(cmd.get("install"))


def _set_doctor(msg: Any, cmd: dict[str, Any]) -> None:
    msg.fix = bool(cmd.get("fix"))
    msg.probe = bool(cmd.get("probe"))
    if cmd.get("probe_prompt"):
        msg.probe_prompt = str(cmd["probe_prompt"])


def _set_calibration(msg: Any, cmd: dict[str, Any]) -> None:
    msg.skip_fix = bool(cmd.get("skip_fix"))
    msg.skip_desktop = bool(cmd.get("skip_desktop"))
    msg.skip_bridge = bool(cmd.get("skip_bridge"))
    if cmd.get("probe_prompt"):
        msg.probe_prompt = str(cmd["probe_prompt"])


def _set_chat(msg: Any, cmd: dict[str, Any]) -> None:
    msg.llm = bool(cmd.get("llm"))
    if cmd.get("shell"):
        msg.shell = str(cmd["shell"])
    msg.single_action = bool(cmd.get("single_action"))


def _set_text(msg: Any, cmd: dict[str, Any]) -> None:
    if cmd.get("target"):
        msg.target = str(cmd["target"])
    msg.llm = bool(cmd.get("llm"))
    if cmd.get("shell"):
        msg.shell = str(cmd["shell"])
    msg.single_action = bool(cmd.get("single_action"))


def _set_sync(msg: Any, cmd: dict[str, Any]) -> None:
    msg.all_ides = bool(cmd.get("all_ides"))


def _set_repair_run(msg: Any, cmd: dict[str, Any]) -> None:
    msg.fix = bool(cmd.get("fix"))
    if cmd.get("ide"):
        msg.ide = str(cmd["ide"])
    if cmd.get("instance"):
        msg.instance = str(cmd["instance"])


_BODY_SETTERS: dict[str, Callable[[Any, dict[str, Any]], None]] = {
    "STATUS": _set_status,
    "ENV": _set_env,
    "QUERY": _set_query,
    "AUTO": _set_auto,
    "LANE": _set_lane,
    "ENSURE": _set_ensure,
    "DOCTOR": _set_doctor,
    "CALIBRATION": _set_calibration,
    "CHAT": _set_chat,
    "TEXT": _set_text,
    "SYNC": _set_sync,
    "REPAIR_RUN": _set_repair_run,
}


def _set_body(envelope: command_pb2.DslEnvelope, cmd: dict[str, Any]) -> None:
    verb = str(cmd.get("verb", "")).upper()
    field = _BODY_MAP.get(verb)
    if not field:
        return
    setter = _BODY_SETTERS.get(verb)
    if setter:
        setter(getattr(envelope, field), cmd)


def dict_to_envelope(cmd: dict[str, Any], *, default_file: str = "", correlation_id: str = "") -> command_pb2.DslEnvelope:
    envelope = command_pb2.DslEnvelope()
    envelope.verb = str(cmd.get("verb", "")).upper()
    _set_body(envelope, cmd)
    envelope.default_file = default_file
    envelope.correlation_id = correlation_id
    return envelope


def _extract_status(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.probe:
        cmd["probe"] = True


def _extract_env(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.file:
        cmd["file"] = msg.file


def _extract_query(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.target:
        cmd["target"] = msg.target


def _extract_auto(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.shell:
        cmd["shell"] = msg.shell
    if msg.auto_args:
        cmd["auto_args"] = list(msg.auto_args)
    if msg.target:
        cmd["target"] = msg.target


def _extract_lane(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.ide:
        cmd["ide"] = msg.ide
    if msg.instance:
        cmd["instance"] = msg.instance
    if msg.file:
        cmd["file"] = msg.file
    if msg.lane_status:
        cmd["lane_status"] = True


def _extract_ensure(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.install:
        cmd["install"] = True


def _extract_doctor(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.fix:
        cmd["fix"] = True
    if msg.probe:
        cmd["probe"] = True
    if msg.probe_prompt:
        cmd["probe_prompt"] = msg.probe_prompt


def _extract_calibration(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.skip_fix:
        cmd["skip_fix"] = True
    if msg.skip_desktop:
        cmd["skip_desktop"] = True
    if msg.skip_bridge:
        cmd["skip_bridge"] = True
    if msg.probe_prompt:
        cmd["probe_prompt"] = msg.probe_prompt


def _extract_chat(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.llm:
        cmd["llm"] = True
    if msg.shell:
        cmd["shell"] = msg.shell
    if msg.single_action:
        cmd["single_action"] = True


def _extract_text(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.target:
        cmd["target"] = msg.target
    if msg.llm:
        cmd["llm"] = True
    if msg.shell:
        cmd["shell"] = msg.shell
    if msg.single_action:
        cmd["single_action"] = True


def _extract_sync(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.all_ides:
        cmd["all_ides"] = True


def _extract_repair_run(msg: Any, cmd: dict[str, Any]) -> None:
    if msg.fix:
        cmd["fix"] = True
    if msg.ide:
        cmd["ide"] = msg.ide
    if msg.instance:
        cmd["instance"] = msg.instance


_BODY_EXTRACTORS: dict[str, Callable[[Any, dict[str, Any]], None]] = {
    "STATUS": _extract_status,
    "ENV": _extract_env,
    "QUERY": _extract_query,
    "AUTO": _extract_auto,
    "LANE": _extract_lane,
    "ENSURE": _extract_ensure,
    "DOCTOR": _extract_doctor,
    "CALIBRATION": _extract_calibration,
    "CHAT": _extract_chat,
    "TEXT": _extract_text,
    "SYNC": _extract_sync,
    "REPAIR_RUN": _extract_repair_run,
}


def envelope_to_dict(envelope: command_pb2.DslEnvelope) -> dict[str, Any]:
    verb = envelope.verb.upper()
    cmd: dict[str, Any] = {"verb": verb}
    field = _BODY_MAP.get(verb)
    if not field or envelope.WhichOneof("body") != field:
        return cmd
    extractor = _BODY_EXTRACTORS.get(verb)
    if extractor:
        extractor(getattr(envelope, field), cmd)
    return cmd


def encode_protobuf(cmd: dict[str, Any], *, default_file: str = "", correlation_id: str = "") -> bytes:
    return dict_to_envelope(cmd, default_file=default_file, correlation_id=correlation_id).SerializeToString()


def decode_protobuf(data: bytes) -> dict[str, Any]:
    envelope = command_pb2.DslEnvelope()
    envelope.ParseFromString(data)
    return envelope_to_dict(envelope)


def encode_text_to_protobuf(line: str, *, default_file: str = "", correlation_id: str = "") -> bytes:
    payload = parse_line(line, default_file=default_file or None)
    if not payload:
        raise ValueError("empty command")
    return encode_protobuf(payload, default_file=default_file, correlation_id=correlation_id)


def decode_protobuf_to_text(data: bytes) -> str:
    return to_text(decode_protobuf(data))


def result_to_pb(result: DslResult) -> result_pb2.DslResult:
    pb = result_pb2.DslResult()
    pb.ok = result.ok
    pb.verb = result.verb
    pb.command = result.command
    pb.action = result.action
    pb.output = result.output
    pb.data_json = json.dumps(result.data, ensure_ascii=False).encode("utf-8")
    pb.error = result.error or ""
    pb.event_id = result.event_id or ""
    return pb


def pb_to_result(pb: result_pb2.DslResult) -> DslResult:
    data: dict[str, Any] = {}
    if pb.data_json:
        try:
            data = json.loads(pb.data_json.decode("utf-8"))
        except json.JSONDecodeError:
            data = {}
    return DslResult(
        ok=pb.ok,
        verb=pb.verb,
        command=pb.command,
        action=pb.action,
        output=pb.output,
        data=data,
        error=pb.error or None,
        event_id=pb.event_id or None,
    )


def encode_result_protobuf(result: DslResult) -> bytes:
    return result_to_pb(result).SerializeToString()
