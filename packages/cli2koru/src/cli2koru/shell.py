"""Interactive shell for dsl2koru."""

from __future__ import annotations

from dsl2koru.bus import execute_dsl_line


def run_shell(*, default_project: str | None = None, json_out: bool = False) -> int:
    import json

    print("cli2koru shell — dsl2koru control (exit/quit to leave)")
    code = 0
    while True:
        try:
            line = input("koru> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in {"exit", "quit", ":q"}:
            break
        result = execute_dsl_line(line, default_project=default_project)
        if json_out:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            if result.error:
                print(f"error: {result.error}")
            if result.output:
                print(result.output.rstrip())
        if not result.ok:
            code = 1
    return code
