"""Decode koru:// URIs into dsl2koru command lines."""

from __future__ import annotations

from uri2koru.uri import parse_koru_uri


def _cmd_uri_to_dsl(
    parts: list[str], params: dict[str, str], project: str
) -> str:
    verb = parts[0].upper() if parts else str(params.get("verb", "")).upper()
    if verb == "QUERY_REPAIR_HISTORY":
        line = f"QUERY_REPAIR_HISTORY PROJECT {project}"
        if params.get("limit"):
            line += f" LIMIT {params['limit']}"
        if params.get("code"):
            line += f" CODE {params['code']}"
        return line
    if verb == "QUERY_LANE_STATUS":
        return (
            f"QUERY_LANE_STATUS IDE {params.get('ide', 'auto')} "
            f"INSTANCE {params.get('instance', 'default')}"
        )
    if verb == "VALIDATE_LANE":
        return (
            f"VALIDATE_LANE IDE {params.get('ide', 'auto')} "
            f"INSTANCE {params.get('instance', 'default')}"
        )
    if verb == "REPAIR_RUN":
        return (
            f"REPAIR_RUN IDE {params.get('ide', 'auto')} "
            f"INSTANCE {params.get('instance', 'default')} PROJECT {project}"
        )
    if verb == "RESOLVE":
        prompt = params.get("prompt", "")
        return f'RESOLVE "{prompt}" PROJECT {project}'
    raise ValueError(f"unsupported cmd uri verb: {verb}")


def _block_uri_to_dsl(parts: list[str], params: dict[str, str], project: str) -> str:
    if parts[:2] == ["repair", "history"]:
        line = f"QUERY_REPAIR_HISTORY PROJECT {project}"
        if params.get("limit"):
            line += f" LIMIT {params['limit']}"
        return line
    if parts[:2] == ["lane", "status"]:
        return (
            f"QUERY_LANE_STATUS IDE {params.get('ide', 'auto')} "
            f"INSTANCE {params.get('instance', 'default')}"
        )
    raise ValueError(f"unsupported block uri: {'/'.join(parts)}")


def uri_to_dsl(uri: str, *, default_project: str | None = None) -> str:
    parsed = parse_koru_uri(uri)
    source = str(parsed["source"])
    parts = list(parsed["parts"])  # type: ignore[arg-type]
    params = dict(parsed["params"])  # type: ignore[arg-type]
    project = str(params.get("project") or default_project or ".")

    if source == "cmd":
        return _cmd_uri_to_dsl(parts, params, project)
    if source == "block":
        return _block_uri_to_dsl(parts, params, project)
    raise ValueError(f"unsupported koru uri source: {source}")
