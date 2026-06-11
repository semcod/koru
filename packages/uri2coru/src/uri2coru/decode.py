"""Decode coru:// URIs into dsl2coru command lines."""

from __future__ import annotations

from typing import Any

from uri2coru.uri import parse_coru_uri


def _context(params: dict[str, str], *, default_file: str | None = None) -> str:
    return str(params.get("default_file") or params.get("project") or default_file or ".")


def _cmd_repair_history(params: dict[str, str], _parts: list[str]) -> str:
    line = "REPAIR_HISTORY"
    if params.get("limit"):
        line += f" LIMIT {params['limit']}"
    return line


def _cmd_lane_status(params: dict[str, str], _parts: list[str]) -> str:
    return (
        f"LANE_STATUS --ide {params.get('ide', 'auto')} "
        f"--instance {params.get('instance', 'default')}"
    )


def _cmd_validate_lane(params: dict[str, str], _parts: list[str]) -> str:
    return (
        f"LANE --ide {params.get('ide', 'auto')} "
        f"--instance {params.get('instance', 'default')}"
    )


def _cmd_repair_run(params: dict[str, str], _parts: list[str]) -> str:
    return (
        f"REPAIR_RUN --ide {params.get('ide', 'auto')} "
        f"--instance {params.get('instance', 'default')}"
    )


def _cmd_resolve(params: dict[str, str], _parts: list[str]) -> str:
    prompt = params.get("prompt", "")
    return f'TEXT "{prompt}"'


def _cmd_status(_params: dict[str, str], _parts: list[str]) -> str:
    return "STATUS"


_CMD_BUILDERS: dict[str, Any] = {
    "REPAIR_HISTORY": _cmd_repair_history,
    "QUERY_REPAIR_HISTORY": _cmd_repair_history,
    "LANE_STATUS": _cmd_lane_status,
    "QUERY_LANE_STATUS": _cmd_lane_status,
    "VALIDATE_LANE": _cmd_validate_lane,
    "LANE": _cmd_validate_lane,
    "REPAIR_RUN": _cmd_repair_run,
    "REPAIR": _cmd_repair_run,
    "RESOLVE": _cmd_resolve,
    "TEXT": _cmd_resolve,
    "STATUS": _cmd_status,
}


def _block_repair_history(params: dict[str, str], _parts: list[str]) -> str:
    line = "REPAIR_HISTORY"
    if params.get("limit"):
        line += f" LIMIT {params['limit']}"
    return line


def _block_lane_status(params: dict[str, str], _parts: list[str]) -> str:
    return (
        f"LANE_STATUS --ide {params.get('ide', 'auto')} "
        f"--instance {params.get('instance', 'default')}"
    )


_BLOCK_BUILDERS: dict[tuple[str, str], Any] = {
    ("repair", "history"): _block_repair_history,
    ("lane", "status"): _block_lane_status,
}


def uri_to_dsl(uri: str, *, default_file: str | None = None, default_project: str | None = None) -> str:
    parsed = parse_coru_uri(uri)
    source = str(parsed["source"])
    parts = list(parsed["parts"])  # type: ignore[arg-type]
    params = dict(parsed["params"])  # type: ignore[arg-type]

    if source == "cmd":
        verb = parts[0].upper() if parts else str(params.get("verb", "")).upper()
        builder = _CMD_BUILDERS.get(verb)
        if builder:
            return builder(params, parts)
        raise ValueError(f"unsupported cmd uri verb: {verb}")

    if source == "block":
        key = tuple(parts[:2]) if len(parts) >= 2 else ()
        builder = _BLOCK_BUILDERS.get(key)
        if builder:
            return builder(params, parts)
        raise ValueError(f"unsupported block uri: {'/'.join(parts)}")

    raise ValueError(f"unsupported coru uri source: {source}")
