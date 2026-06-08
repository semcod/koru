"""MCP tool implementations — testable without stdio server."""

from __future__ import annotations

from typing import Any


def koru_run_command(command: str, project: str = ".") -> dict[str, Any]:
    from dsl2koru.bus import dispatch

    return dispatch(command, default_project=project).to_dict()


def koru_run_dsl(script: str, project: str = ".") -> list[dict[str, Any]]:
    from dsl2koru.bus import execute_dsl

    return [r.to_dict() for r in execute_dsl(script, default_project=project)]


def koru_run_command_pb(envelope_bytes: bytes, project: str = ".") -> bytes:
    from dsl2koru.bus import dispatch
    from dsl2koru.pb_codec import encode_result_protobuf

    return encode_result_protobuf(dispatch(envelope_bytes, default_project=project))


def koru_to_dsl(prompt: str, project: str = ".") -> str:
    from nlp2koru.to_dsl import to_dsl

    return to_dsl(prompt, project=project)
