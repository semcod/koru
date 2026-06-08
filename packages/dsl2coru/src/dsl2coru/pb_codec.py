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


def _set_body(envelope: command_pb2.DslEnvelope, cmd: dict[str, Any]) -> None:
    verb = str(cmd.get("verb", "")).upper()
    field = _BODY_MAP.get(verb)
    if not field:
        return
    msg = getattr(envelope, field)
    if verb == "STATUS":
        msg.probe = bool(cmd.get("probe"))
    elif verb == "ENV":
        if cmd.get("file"):
            msg.file = str(cmd["file"])
    elif verb == "QUERY":
        if cmd.get("target"):
            msg.target = str(cmd["target"])
    elif verb == "AUTO":
        if cmd.get("shell"):
            msg.shell = str(cmd["shell"])
        if args := cmd.get("auto_args"):
            if isinstance(args, str):
                msg.auto_args.extend(args.split())
            else:
                msg.auto_args.extend([str(item) for item in args])
        if cmd.get("target"):
            msg.target = str(cmd["target"])
    elif verb == "LANE":
        if cmd.get("ide"):
            msg.ide = str(cmd["ide"])
        if cmd.get("instance"):
            msg.instance = str(cmd["instance"])
        if cmd.get("file"):
            msg.file = str(cmd["file"])
        msg.lane_status = bool(cmd.get("lane_status"))
    elif verb == "ENSURE":
        msg.install = bool(cmd.get("install"))
    elif verb == "DOCTOR":
        msg.fix = bool(cmd.get("fix"))
        msg.probe = bool(cmd.get("probe"))
        if cmd.get("probe_prompt"):
            msg.probe_prompt = str(cmd["probe_prompt"])
    elif verb == "CALIBRATION":
        msg.skip_fix = bool(cmd.get("skip_fix"))
        msg.skip_desktop = bool(cmd.get("skip_desktop"))
        msg.skip_bridge = bool(cmd.get("skip_bridge"))
        if cmd.get("probe_prompt"):
            msg.probe_prompt = str(cmd["probe_prompt"])
    elif verb == "CHAT":
        msg.llm = bool(cmd.get("llm"))
        if cmd.get("shell"):
            msg.shell = str(cmd["shell"])
        msg.single_action = bool(cmd.get("single_action"))
    elif verb == "TEXT":
        if cmd.get("target"):
            msg.target = str(cmd["target"])
        msg.llm = bool(cmd.get("llm"))
        if cmd.get("shell"):
            msg.shell = str(cmd["shell"])
        msg.single_action = bool(cmd.get("single_action"))
    elif verb == "SYNC":
        msg.all_ides = bool(cmd.get("all_ides"))
    elif verb == "REPAIR_RUN":
        msg.fix = bool(cmd.get("fix"))
        if cmd.get("ide"):
            msg.ide = str(cmd["ide"])
        if cmd.get("instance"):
            msg.instance = str(cmd["instance"])


def dict_to_envelope(cmd: dict[str, Any], *, default_file: str = "", correlation_id: str = "") -> command_pb2.DslEnvelope:
    envelope = command_pb2.DslEnvelope()
    envelope.verb = str(cmd.get("verb", "")).upper()
    _set_body(envelope, cmd)
    envelope.default_file = default_file
    envelope.correlation_id = correlation_id
    return envelope


def envelope_to_dict(envelope: command_pb2.DslEnvelope) -> dict[str, Any]:
    verb = envelope.verb.upper()
    cmd: dict[str, Any] = {"verb": verb}
    field = _BODY_MAP.get(verb)
    if not field:
        return cmd
    if envelope.WhichOneof("body") != field:
        return cmd
    msg = getattr(envelope, field)
    if verb == "STATUS":
        if msg.probe:
            cmd["probe"] = True
    elif verb == "ENV":
        if msg.file:
            cmd["file"] = msg.file
    elif verb == "QUERY":
        if msg.target:
            cmd["target"] = msg.target
    elif verb == "AUTO":
        if msg.shell:
            cmd["shell"] = msg.shell
        if msg.auto_args:
            cmd["auto_args"] = list(msg.auto_args)
        if msg.target:
            cmd["target"] = msg.target
    elif verb == "LANE":
        if msg.ide:
            cmd["ide"] = msg.ide
        if msg.instance:
            cmd["instance"] = msg.instance
        if msg.file:
            cmd["file"] = msg.file
        if msg.lane_status:
            cmd["lane_status"] = True
    elif verb == "ENSURE":
        if msg.install:
            cmd["install"] = True
    elif verb == "DOCTOR":
        if msg.fix:
            cmd["fix"] = True
        if msg.probe:
            cmd["probe"] = True
        if msg.probe_prompt:
            cmd["probe_prompt"] = msg.probe_prompt
    elif verb == "CALIBRATION":
        if msg.skip_fix:
            cmd["skip_fix"] = True
        if msg.skip_desktop:
            cmd["skip_desktop"] = True
        if msg.skip_bridge:
            cmd["skip_bridge"] = True
        if msg.probe_prompt:
            cmd["probe_prompt"] = msg.probe_prompt
    elif verb == "CHAT":
        if msg.llm:
            cmd["llm"] = True
        if msg.shell:
            cmd["shell"] = msg.shell
        if msg.single_action:
            cmd["single_action"] = True
    elif verb == "TEXT":
        if msg.target:
            cmd["target"] = msg.target
        if msg.llm:
            cmd["llm"] = True
        if msg.shell:
            cmd["shell"] = msg.shell
        if msg.single_action:
            cmd["single_action"] = True
    elif verb == "SYNC":
        if msg.all_ides:
            cmd["all_ides"] = True
    elif verb == "REPAIR_RUN":
        if msg.fix:
            cmd["fix"] = True
        if msg.ide:
            cmd["ide"] = msg.ide
        if msg.instance:
            cmd["instance"] = msg.instance
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
