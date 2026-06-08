"""Thin shim — route control verbs through dsl2koru / dsl2coru bus."""

from __future__ import annotations

_DSL2KORU_VERBS = frozenset({"QUERY_REPAIR_HISTORY", "QUERY_LANE_STATUS", "VALIDATE_LANE", "RESOLVE", "REPAIR_RUN"})


def dispatch_line(line: str, *, default_project: str | None = None) -> dict:
    stripped = line.strip()
    if not stripped:
        return {"ok": True, "verb": "noop"}
    verb = stripped.split()[0].upper()
    if verb in _DSL2KORU_VERBS:
        from dsl2koru.bus import dispatch

        return dispatch(stripped, default_project=default_project).to_dict()
    from dsl2coru.bus import dispatch

    return dispatch(stripped, default_project=default_project).to_dict()


def dispatch_repair_history(*, project: str = ".", limit: int = 20, code: str | None = None) -> dict:
    parts = [f"QUERY_REPAIR_HISTORY PROJECT {project}", f"LIMIT {limit}"]
    if code:
        parts.append(f"CODE {code}")
    return dispatch_line(" ".join(parts), default_project=project)


def dispatch_validate_lane(*, ide: str = "auto", instance: str = "default") -> dict:
    return dispatch_line(f"VALIDATE_LANE IDE {ide} INSTANCE {instance}")


def dispatch_status() -> dict:
    return dispatch_line("STATUS")


def apply_nl(
    prompt: str,
    *,
    use_llm: bool = False,
    single_action: bool = False,
    default_project: str | None = None,
) -> int:
    """NL → nlp2coru → dsl2coru/dsl2koru dispatch. Returns shell exit code."""
    from nlp2coru.apply import apply_prompt

    result = apply_prompt(
        prompt,
        use_llm=use_llm,
        default_file=default_project,
        single_action=single_action,
    )
    if result.error:
        import sys

        print(result.error, file=sys.stderr)
    for item in result.results:
        if item.get("error"):
            import sys

            print(f"error: {item['error']}", file=sys.stderr)
        if item.get("output"):
            print(str(item["output"]).rstrip())
    return 0 if result.ok else 1
