import argparse
from pathlib import Path
from typing import Any

from koru.events import emit_management_event
from koru.tasks import create_nl_task
from koru.tools import build_tool_task_scaffold, find_tool_entry, load_tool_registry


def _build_task_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru task",
        description="Create a planfile ticket from a natural-language sentence.",
    )
    parser.add_argument("text", nargs="+", help="Natural-language task description.")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument("--sprint", default="current", help="Target planfile sprint.")
    parser.add_argument("--queue-name", default=None, help="Execution queue for the new ticket.")
    parser.add_argument("--priority", default="normal", help="Ticket priority.")
    parser.add_argument(
        "--source-tool",
        default=None,
        help="Producer id stored in ticket source.tool (for plugin/tool intake).",
    )
    parser.add_argument(
        "--source-signal",
        default=None,
        help="Producer signal stored in source.context.signal.",
    )
    parser.add_argument(
        "--dedupe-key",
        default=None,
        help=(
            "Stable issue key shared by producers; an existing ticket with the same "
            "key is reused instead of creating a duplicate."
        ),
    )
    parser.add_argument(
        "--files",
        action="append",
        default=[],
        help="File path associated with the ticket. Repeat for multiple files.",
    )
    parser.add_argument(
        "--tool",
        dest="tool_id",
        default=None,
        help=(
            "Build a tool-adapter scaffold ticket for this tool id "
            "(from docs/ai-tool-registry-2026.yaml)."
        ),
    )
    parser.add_argument(
        "--tool-kind",
        dest="tool_kind",
        choices=("human", "shell", "api", "llm"),
        default=None,
        help="Override scaffolded executor hint for --tool.",
    )
    parser.add_argument(
        "--tool-registry",
        dest="tool_registry",
        type=Path,
        default=None,
        help="Override tool registry path for --tool lookup.",
    )
    return parser


def _load_tool_scaffold(
    tool_id: str,
    tool_registry: str | None,
    tool_kind: str | None,
) -> tuple[dict[str, Any] | None, Path | None, int | None]:
    """Load scaffold from tool registry. Returns (scaffold, registry_path, error_code)."""
    registry, registry_path = load_tool_registry(tool_registry)
    if not registry:
        print(
            "koru task: tool registry is empty or missing. "
            "Use --tool-registry PATH or ensure docs/ai-tool-registry-2026.yaml exists.",
        )
        return None, None, 2
    tool = find_tool_entry(registry, tool_id)
    if tool is None:
        known = ", ".join(sorted(str(t.get("id")) for t in registry if t.get("id")))
        print(f"koru task: unknown --tool '{tool_id}'. Known ids: {known}")
        return None, None, 2
    scaffold = build_tool_task_scaffold(tool, adapter_kind=tool_kind)
    if registry_path is not None:
        scaffold.setdefault("source_context", {})
        if isinstance(scaffold.get("source_context"), dict):
            scaffold["source_context"]["registry"] = str(registry_path)
    return scaffold, registry_path, None


def _merge_cli_scaffold(
    scaffold: dict[str, Any] | None,
    *,
    source_tool: str | None,
    source_signal: str | None,
    dedupe_key: str | None,
    files: list[str] | None,
) -> dict[str, Any] | None:
    if not (source_tool or source_signal or dedupe_key or files):
        return scaffold
    scaffold = dict(scaffold or {})
    if source_tool:
        scaffold["source_tool"] = source_tool
    context = (
        dict(scaffold.get("source_context"))
        if isinstance(scaffold.get("source_context"), dict)
        else {}
    )
    if source_signal:
        context["signal"] = source_signal
    if dedupe_key:
        context["dedupe_key"] = dedupe_key
    scaffold["source_context"] = context
    if files:
        scaffold["files"] = list(files)
    return scaffold


def _print_task_result(created: object, args: Any) -> None:
    action = "reused" if getattr(created, "reused", False) else "created"
    print(f"koru task: ✓ {action} {created.ticket_id} in {created.path}")
    print(f"  name:  {created.name}")
    print(f"  queue: {args.queue_name or 'default'}")
    if args.tool_id:
        print(f"  tool:  {args.tool_id}")
        print("  note: scaffold ticket created — fill concrete executor inputs before queue run")
    print("Next: run `koru` to get the LLM prompt, or `koru --queue` to execute one task.")
    emit_management_event(
        tool="koru.task",
        action="created",
        status="completed",
        message=created.name,
        queue=args.queue_name,
        details={
            "ticket_id": created.ticket_id,
            "project": str(args.project),
            "sprint": args.sprint,
            "priority": args.priority,
        },
    )


def _task_main(argv: list[str]) -> int:
    args = _build_task_parser().parse_args(argv)
    scaffold: dict[str, Any] | None = None

    if args.tool_id:
        scaffold, _registry_path, error_code = _load_tool_scaffold(
            args.tool_id,
            args.tool_registry,
            args.tool_kind,
        )
        if error_code is not None:
            return error_code

    scaffold = _merge_cli_scaffold(
        scaffold,
        source_tool=args.source_tool,
        source_signal=args.source_signal,
        dedupe_key=args.dedupe_key,
        files=args.files,
    )

    try:
        created = create_nl_task(
            args.project,
            " ".join(args.text),
            sprint=args.sprint,
            queue_name=args.queue_name,
            priority=args.priority,
            scaffold=scaffold,
        )
    except ValueError as exc:
        print(f"koru task: {exc}")
        return 2
    _print_task_result(created, args)
    return 0

