"""CLI entrypoint for daily execution summary: ``koru sum`` and ``koru summary``."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


def _standalone_gather_summary(root: Path) -> dict:
    """Fallback collector when monag package is not present in the environment."""
    today_str = date.today().isoformat()
    done_tickets: list[dict] = []
    queued_tickets: list[dict] = []

    target_root = root if root.is_dir() else Path.cwd()
    sprint_dirs: list[Path] = []
    if (target_root / ".planfile" / "sprints").is_dir():
        sprint_dirs.append(target_root / ".planfile" / "sprints")

    for s_dir in sprint_dirs:
        curr_yaml = s_dir / "current.yaml"
        if curr_yaml.is_file():
            try:
                import yaml

                content = yaml.safe_load(curr_yaml.read_text(encoding="utf-8")) or {}
                tickets = content.get("tickets", {})
                for tid, t in tickets.items():
                    status = (t.get("status") or "open").lower()
                    name = t.get("name") or t.get("description", tid)[:60]
                    if status in ("done", "closed"):
                        done_tickets.append({"repo": target_root.name, "id": tid, "title": name})
                    else:
                        queued_tickets.append({
                            "repo": target_root.name,
                            "id": tid,
                            "title": name,
                            "priority": t.get("priority", "normal"),
                            "estimate_minutes": 5,
                        })
            except Exception:
                pass

    return {
        "date": today_str,
        "planfile": {
            "completed_today": done_tickets,
            "queue": queued_tickets,
            "total_completed_today": len(done_tickets),
            "total_queued": len(queued_tickets),
            "total_estimate_minutes": len(queued_tickets) * 5,
        },
        "prs": {
            "open": [],
            "merged_today": [],
            "total_open": 0,
            "total_merged_today": 0,
        },
    }


def _standalone_format_markdown(data: dict) -> str:
    """Fallback Markdown formatter matching MONAG summary structure."""
    d = data.get("date", "today")
    pf = data.get("planfile", {})
    prs = data.get("prs", {})
    return f"""# MONAG Daily Execution Summary ({d})

## 1. Planfile & Koru Living Execution
- **Wykonane dzisiaj**: `{pf.get('total_completed_today', 0)}` zadań
- **Oczekujące w kolejce**: `{pf.get('total_queued', 0)}` zadań (szacunkowo `{pf.get('total_estimate_minutes', 0)} min`)

## 2. GitHub Pull Requests
- **Otwarte PR w kolejce**: `{prs.get('total_open', 0)}`
- **Zmergowane dzisiaj (>= {d})**: `{prs.get('total_merged_today', 0)}`
"""


def summary_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="koru sum",
        description="Daily execution summary: Planfile completed/queued tasks, GitHub PRs and duration estimates.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/home/tom/github"),
        help="Workspace root containing target repositories (default: /home/tom/github)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON summary document",
    )
    parser.add_argument(
        "--raw",
        "--markdown",
        "-m",
        action="store_true",
        help="Output raw Markdown without terminal formatting (ideal for redirects or piping)",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Output plain text without ANSI escape sequences or Markdown styling",
    )
    parser.add_argument(
        "--no-github",
        dest="github",
        action="store_false",
        default=True,
        help="Skip querying GitHub PR status via gh CLI",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=24.0,
        help="Time window in hours for daily recency (default: 24.0)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Directory depth to scan for Planfile repositories (default: 3)",
    )
    args = parser.parse_args(argv)

    try:
        try:
            from monag import summary as monag_summary

            data = monag_summary.gather_summary(
                root=args.root,
                hours=args.hours,
                github=args.github,
                depth=args.depth,
            )
            md_text = monag_summary.format_markdown(data)
        except ImportError:
            data = _standalone_gather_summary(root=args.root)
            md_text = _standalone_format_markdown(data)

        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            from koru.terminal_render import render_markdown

            render_markdown(
                md_text,
                force_raw=args.raw,
                force_plain=args.plain,
            )
        return 0
    except Exception as exc:
        print(f"koru sum: error gathering daily execution summary: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(summary_main(sys.argv[1:]))

