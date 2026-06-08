"""Decode coru:// URIs into dsl2coru command lines."""

from __future__ import annotations

from uri2coru.uri import parse_coru_uri


def _context(params: dict[str, str], *, default_file: str | None = None) -> str:
    return str(params.get("default_file") or params.get("project") or default_file or ".")


def uri_to_dsl(uri: str, *, default_file: str | None = None, default_project: str | None = None) -> str:
    parsed = parse_coru_uri(uri)
    source = str(parsed["source"])
    parts = list(parsed["parts"])  # type: ignore[arg-type]
    params = dict(parsed["params"])  # type: ignore[arg-type]
    ctx = _context(params, default_file=default_file or default_project)

    if source == "cmd":
        verb = parts[0].upper() if parts else str(params.get("verb", "")).upper()
        if verb in {"REPAIR_HISTORY", "QUERY_REPAIR_HISTORY"}:
            line = "REPAIR_HISTORY"
            if params.get("limit"):
                line += f" LIMIT {params['limit']}"
            return line
        if verb in {"LANE_STATUS", "QUERY_LANE_STATUS"}:
            return (
                f"LANE_STATUS --ide {params.get('ide', 'auto')} "
                f"--instance {params.get('instance', 'default')}"
            )
        if verb in {"VALIDATE_LANE", "LANE"}:
            return (
                f"LANE --ide {params.get('ide', 'auto')} "
                f"--instance {params.get('instance', 'default')}"
            )
        if verb in {"REPAIR_RUN", "REPAIR"}:
            return (
                f"REPAIR_RUN --ide {params.get('ide', 'auto')} "
                f"--instance {params.get('instance', 'default')}"
            )
        if verb in {"RESOLVE", "TEXT"}:
            prompt = params.get("prompt", "")
            return f'TEXT "{prompt}"'
        if verb == "STATUS":
            return "STATUS"
        raise ValueError(f"unsupported cmd uri verb: {verb}")

    if source == "block":
        if parts[:2] == ["repair", "history"]:
            line = "REPAIR_HISTORY"
            if params.get("limit"):
                line += f" LIMIT {params['limit']}"
            return line
        if parts[:2] == ["lane", "status"]:
            return (
                f"LANE_STATUS --ide {params.get('ide', 'auto')} "
                f"--instance {params.get('instance', 'default')}"
            )
        raise ValueError(f"unsupported block uri: {'/'.join(parts)}")

    raise ValueError(f"unsupported coru uri source: {source}")
