#!/usr/bin/env python3
"""Two-way sync between planfile tickets and a human markdown list.

Design
------
The human list path, labels, and how ``done`` tickets appear are controlled by
``.planfile/config.yaml`` under ``koru.markdown_todo`` (see defaults in
``planfile_sync_todo_settings.py``). ``koru.yaml`` documents *when* to run this
script (``task planfile:sync-todo``).

  planfile → markdown
    Tickets matching the active profile are mirrored under the
    "## 🤖 Auto-generated (from planfile)" section.

  markdown → planfile
    Lines matching ``- [ ]`` under an H2/H3 heading are imported as tickets;
    labels come from ``markdown_to_planfile.import_labels`` in config.

Modes:
  --from-planfile     planfile → markdown (default)
  --from-todo HEADING markdown → planfile for the given H2/H3 heading
  --check             report diff without writing

The script is idempotent — re-running it on an already-synced tree is a
no-op.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def _find_scripts_dir_with_settings() -> Path:
    """Locate ``planfile_sync_todo_settings.py`` (supports symlinked entrypoints)."""
    cwd_scripts = Path.cwd().resolve() / "scripts"
    if (cwd_scripts / "planfile_sync_todo_settings.py").is_file():
        return cwd_scripts
    here_scripts = Path(__file__).resolve().parent
    if (here_scripts / "planfile_sync_todo_settings.py").is_file():
        return here_scripts
    raise SystemExit(
        "planfile_sync_todo_settings.py not found in ./scripts (cwd) or next to "
        "this script. Run from the project root (e.g. cd …/c2004)."
    )


_SCRIPTS_DIR = _find_scripts_dir_with_settings()
REPO = Path.cwd().resolve()
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from planfile_sync_todo_settings import (
    AUTO_END,
    AUTO_HEADER,
    human_list_path,
    markdown_to_planfile_settings,
    planfile_to_markdown_settings,
    render_auto_generated_markdown,
)


def run_planfile(*args: str) -> str:
    """Invoke the planfile CLI with stderr silenced (pydantic warnings pollute it)."""
    cmd = ["planfile", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, timeout=15)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"planfile {' '.join(args)} failed ({proc.returncode})")
    return proc.stdout


def load_tickets() -> list[dict]:
    """Prefer YAML because planfile's JSON mode can emit raw control chars in
    description blocks. PyYAML round-trips them correctly; json.loads chokes."""
    raw = run_planfile("ticket", "list", "--status", "all", "--format", "yaml")
    try:
        import yaml  # local import; only this script needs it
    except ImportError:  # pragma: no cover
        sys.stderr.write("PyYAML not installed; falling back to json (may lose tickets)\n")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []
    try:
        data = yaml.safe_load(raw) or []
        return data if isinstance(data, list) else []
    except Exception:
        return []


def build_auto_section(tickets: list[dict]) -> str:
    p2m = planfile_to_markdown_settings(REPO)
    return render_auto_generated_markdown(tickets, p2m)


def replace_auto_section(current: str, new_section: str) -> str:
    if AUTO_HEADER not in current:
        sep = "" if current.endswith("\n\n") else ("\n" if current.endswith("\n") else "\n\n")
        return current + sep + new_section
    # Replace from AUTO_HEADER to AUTO_END (inclusive).
    pattern = re.compile(
        rf"{re.escape(AUTO_HEADER)}.*?{re.escape(AUTO_END)}\n?",
        re.DOTALL,
    )
    return pattern.sub(new_section, current)


def do_from_planfile(check: bool) -> int:
    tickets = load_tickets()
    todo_file = human_list_path(REPO)
    p2m = planfile_to_markdown_settings(REPO)
    new_section = build_auto_section(tickets)
    current = todo_file.read_text(encoding="utf-8") if todo_file.exists() else ""
    updated = replace_auto_section(current, new_section)
    label = todo_file.name
    if updated == current:
        print(f"{label} already in sync with planfile")
        return 0
    if check:
        print(f"{label} would change (use without --check to write):")
        # Show a small diff summary, not the whole file.
        diff_lines = [ln for ln in updated.splitlines() if ln.startswith("- [ ] **PLF")]
        for ln in diff_lines[:10]:
            print("  +", ln)
        return 1
    todo_file.write_text(updated, encoding="utf-8")
    required = p2m.get("required_labels") or ["llm-ready"]
    if not isinstance(required, list):
        required = ["llm-ready"]
    n_match = sum(
        1
        for t in tickets
        if isinstance(t, dict) and all(x in (t.get("labels") or []) for x in required)
    )
    print(f"wrote {todo_file} ({n_match} ticket(s) matching profile labels)")
    return 0


def do_from_todo(heading: str, check: bool) -> int:
    todo_file = human_list_path(REPO)
    if not todo_file.exists():
        print(f"{todo_file.name} not found; nothing to import", file=sys.stderr)
        return 2
    text = todo_file.read_text(encoding="utf-8")
    # Grab everything under `## <heading>` or `### <heading>` until the next heading of equal/higher level.
    pattern = re.compile(
        rf"^(#{2, 3})\s+{re.escape(heading)}\s*$(.*?)(?=^\1\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        print(f"heading '{heading}' not found in {todo_file.name}", file=sys.stderr)
        return 2
    body = match.group(2)
    items = re.findall(r"^\s*-\s*\[ \]\s+(.+?)\s*$", body, re.MULTILINE)
    if not items:
        print("no open items under that heading")
        return 0

    m2p = markdown_to_planfile_settings(REPO)
    import_labels = m2p.get("import_labels") or ["imported-from-todo", "llm-ready"]
    if not isinstance(import_labels, list):
        import_labels = ["imported-from-todo", "llm-ready"]
    import_labels = [str(x) for x in import_labels if str(x).strip()]

    existing_names = {t.get("name") or "" for t in load_tickets()}
    created: list[str] = []
    for item in items:
        name = f"[{todo_file.name}] {item}"
        if any(name in n for n in existing_names):
            continue
        if check:
            created.append(name)
            continue
        cmd: list[str] = [
            "planfile",
            "ticket",
            "create",
            name,
            "--priority",
            "normal",
            "--source",
            todo_file.name,
        ]
        for lab in import_labels:
            cmd.extend(["--label", lab])
        cmd.extend(["--description", _llm_stub(item, heading, todo_file.name)])
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, timeout=60)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr or "")
            raise SystemExit(f"planfile ticket create failed ({proc.returncode})")
        created.append(name)
    action = "would create" if check else "created"
    print(f"{action} {len(created)} ticket(s)")
    for n in created[:10]:
        print("  -", n)
    return 0


def _llm_stub(item: str, heading: str, source_name: str) -> str:
    return (
        f"## 🚨 Context\n\n- **Source:** {source_name} → {heading}\n- **Task:** {item}\n\n"
        "## 🔁 Reproduction\n\n(Task doesn't have a reproduction yet — document it "
        "before starting.)\n\n## ✅ Acceptance criteria\n\n- [ ] Task satisfied per "
        "its description\n- [ ] No new regression in `task test`\n- [ ] `redsl gate "
        "check` passes\n\n## 🔒 Constraints\n\n- Keep the diff minimal and focused "
        "on this item.\n- If scope balloons, split into multiple tickets.\n\n"
        "## 🤖 Prompt (LLM-agnostic)\n\n> Work the task described above. Use the "
        "c2004 Taskfile and redsl.yaml gates for validation.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument(
        "--from-planfile", action="store_true", help="sync tickets → human list (default)"
    )
    grp.add_argument("--from-todo", metavar="HEADING", help="import items under an H2/H3 heading")
    ap.add_argument("--check", action="store_true", help="don't write, report diff only")
    args = ap.parse_args()

    if args.from_todo:
        return do_from_todo(args.from_todo, args.check)
    return do_from_planfile(args.check)


if __name__ == "__main__":
    sys.exit(main())
