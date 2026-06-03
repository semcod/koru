import argparse
import json
import sys
from pathlib import Path

from koru.events import emit_management_event
from koru.tools import detect_tools, load_tool_registry, render_tools_detect_text


def _build_tools_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru tools",
        description="Inspect AI tool registry/detection status.",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)
    detect = sub.add_parser("detect", help="Detect tools from the 2026 registry.")
    detect.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    detect.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="Override registry YAML path (default: docs/ai-tool-registry-2026.yaml).",
    )
    detect.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    return parser


def _tools_main(argv: list[str]) -> int:
    args = _build_tools_parser().parse_args(argv)
    if args.subcommand != "detect":
        print(f"koru tools: unknown subcommand {args.subcommand!r}", file=sys.stderr)
        return 2

    registry, registry_path = load_tool_registry(args.registry)
    results = detect_tools(args.project.resolve(), registry)

    if args.output_format == "json":
        payload = {
            "project": str(args.project),
            "registry": str(registry_path) if registry_path else None,
            "tools": results,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_tools_detect_text(results, registry_path=registry_path))

    emit_management_event(
        tool="koru.tools.detect",
        action="completed",
        status="completed",
        message=f"tools={len(results)}",
        details={
            "project": str(args.project),
            "registry": str(registry_path) if registry_path else None,
            "available": sum(1 for r in results if r.get("available")),
        },
    )
    return 0
