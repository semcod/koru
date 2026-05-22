import argparse
import json
import sys

def agent_backends_main(argv: list[str]) -> int:
    """List or describe IDE agent backend profiles (``agent_backends``)."""
    from dataclasses import asdict

    from koru.agent_backends import get_agent_backend_profile, iter_agent_backend_profiles

    parser = argparse.ArgumentParser(prog="koru agent-backends")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
    )
    parser.add_argument(
        "backend_id",
        nargs="?",
        default=None,
        metavar="BACKEND_ID",
        help="When set, print one profile; otherwise list every profile id.",
    )
    args = parser.parse_args(argv)

    if args.backend_id:
        profile = get_agent_backend_profile(args.backend_id)
        if profile is None:
            sys.stderr.write(f"koru agent-backends: unknown id {args.backend_id!r}\n")
            sys.stderr.write("  run `koru agent-backends` for ids.\n")
            return 2
    else:
        profile = None

    if args.output_format == "json":
        if profile:
            print(json.dumps(asdict(profile), indent=2, sort_keys=True))
        else:
            print(
                json.dumps(
                    [asdict(p) for p in iter_agent_backend_profiles()],
                    indent=2,
                    sort_keys=True,
                ),
            )
        return 0

    if profile:
        print(f"id                 {profile.id}")
        print(f"transport          {profile.transport}")
        print(f"can_push_chat      {profile.can_push_chat}")
        print(f"can_pull_chat_text {profile.can_pull_chat_text}")
        print(f"needs_gui_session  {profile.needs_gui_session}")
        print(f"mcp_tools_only     {profile.mcp_tools_only}")
        print(f"primary_code       {profile.primary_code}")
        return 0

    for p in iter_agent_backend_profiles():
        print(p.id)
    return 0
