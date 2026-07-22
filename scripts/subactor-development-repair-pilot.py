#!/usr/bin/env python3
"""One-shot real-LLM pilot for Subactor development_defect → Koru patch queue.

Creates an isolated git fixture under /tmp, imports a rendered
``subactor-development-repair`` ticket, and runs ``koru --queue`` once with
OpenRouter credentials from ``<koru-root>/.env``.

Planfile's ``TicketInputs`` schema keeps ``llm_model`` and ``executor`` but drops
Koru-only patch policy keys (``patch_mode``, ``verify_command``, …). The queue
restores those from the packaged template (``hydrate_subactor_repair_ticket``)
when labels include ``source:subactor-bridge``. ``verify_command`` also falls
back to ``acceptance_criteria`` and ``KORU_QUEUE_VERIFY_COMMAND``.

Usage:
  python scripts/subactor-development-repair-pilot.py
  python scripts/subactor-development-repair-pilot.py --keep /tmp/my-pilot

Never touches Plesk, DNS, or ``subactor ask --apply``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KORU_ROOT = Path(__file__).resolve().parents[1]


def _load_koru_dotenv() -> None:
    from koru.dotenv_loader import load_dotenv

    load_dotenv(KORU_ROOT)


def _require_llm_env() -> dict[str, str]:
    missing = [name for name in ("OPENROUTER_API_KEY", "LLM_MODEL") if not os.getenv(name)]
    if missing:
        raise SystemExit(f"missing required env vars: {', '.join(missing)}")
    return {
        "OPENROUTER_API_KEY": "set",
        "LLM_MODEL": os.environ["LLM_MODEL"],
    }


def _normalize_model(model: str) -> str:
    return model.removeprefix("openrouter/") if model.startswith("openrouter/") else model


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def _init_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "broken.mjs").write_text(
        "// Intentional syntax defect for Koru real-LLM pilot.\n"
        "export function greet(name) {\n"
        "  return `hello ${name}`\n"
        "// missing closing brace\n",
        encoding="utf-8",
    )
    (root / "tests" / "broken.test.mjs").write_text(
        "import test from 'node:test';\n"
        "import assert from 'node:assert/strict';\n"
        "import { greet } from '../src/broken.mjs';\n\n"
        "test('greet returns hello', () => {\n"
        "  assert.equal(greet('world'), 'hello world');\n"
        "});\n",
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        '{"name":"koru-subactor-pilot-fixture","type":"module","private":true}\n',
        encoding="utf-8",
    )
    _run(["git", "init"], cwd=root)
    _run(["git", "config", "user.email", "pilot@koru.local"], cwd=root)
    _run(["git", "config", "user.name", "Koru Pilot"], cwd=root)
    _run(["git", "add", "-A"], cwd=root)
    _run(["git", "commit", "-m", "fixture: broken greet for pilot"], cwd=root)


def _init_planfile(root: Path) -> None:
    planfile = root / ".planfile"
    (planfile / "sprints").mkdir(parents=True)
    (planfile / "config.yaml").write_text(
        "next_id: 1\nprefix: PILOT\nproject: koru-subactor-pilot\n",
        encoding="utf-8",
    )
    (planfile / "sprints" / "current.yaml").write_text(
        "sprint:\n  id: current\n  name: koru-subactor-pilot\n  status: active\n  tickets: {}\n",
        encoding="utf-8",
    )


def _render_ticket() -> dict:
    from koru.queue.ticket_templates import render_subactor_repair_ticket

    verify = "node --check src/broken.mjs && node --test tests/broken.test.mjs"
    ticket = render_subactor_repair_ticket(
        {
            "COMPONENT": "pilot-fixture",
            "ERROR_CODE": "syntax_error",
            "FINGERPRINT": "pilot-fixture:syntax_error",
            "DISCOVERED_IN": "PILOT-001",
            "FILE_1": "src/broken.mjs",
            "FILE_2": "tests/broken.test.mjs",
            "PROMPT_BODY": (
                "Fix the syntax error in src/broken.mjs so node --check passes. "
                "Keep greet() returning `hello ${name}`."
            ),
        },
    )
    ticket["inputs"]["verify_command"] = verify
    ticket["acceptance_criteria"] = [verify]
    ticket["queue"] = "development"
    return ticket


def _import_ticket(root: Path, ticket: dict) -> str:
    import_path = root / ".planfile" / "pilot-ticket.json"
    import_path.write_text(json.dumps([ticket]), encoding="utf-8")
    proc = subprocess.run(
        [
            "planfile",
            "ticket",
            "import",
            "--source",
            "koru-subactor-pilot",
            "--from",
            str(import_path),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr or proc.stdout or "planfile import failed")
    listed = _run(
        ["planfile", "ticket", "list", "--status", "open", "--format", "json"],
        cwd=root,
    )
    tickets = json.loads(listed.stdout or "[]")
    if not tickets:
        raise SystemExit("no open ticket after import")
    return str(tickets[0]["id"])


def _queue_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("KORU_LLM_SHELL_FALLBACK", "0")
    return env


def _run_queue(root: Path) -> subprocess.CompletedProcess[str]:
    koru = KORU_ROOT / "scripts" / "koru-from-repo.sh"
    return _run(
        [
            str(koru),
            "--queue",
            "--project",
            str(root),
            "--actor",
            "subactor-pilot",
            "--no-log",
        ],
        cwd=KORU_ROOT,
        env=_queue_env(root),
    )


def _collect_evidence(root: Path) -> dict:
    listed = _run(["git", "branch", "--list", "koru/run-*"], cwd=root).stdout or ""
    branches = [line.strip().lstrip("* ").strip() for line in listed.splitlines() if line.strip()]
    verify_cmd = "node --check src/broken.mjs && node --test tests/broken.test.mjs"

    # promotion_mode=branch leaves the working tree deliberately broken — the fix
    # lives on koru/run-<id>. Verifying the tree therefore always failed and said
    # nothing about the patch, so check the branch out and verify that instead.
    target = branches[0] if branches else None
    if target:
        checkout = Path(tempfile.mkdtemp(prefix="koru-pilot-verify-"))
        shutil.rmtree(checkout, ignore_errors=True)
        _run(["git", "worktree", "add", "--detach", "--quiet", str(checkout), target], cwd=root)
        try:
            verify = _run(["bash", "-lc", verify_cmd], cwd=checkout)
        finally:
            _run(["git", "worktree", "remove", "--force", str(checkout)], cwd=root)
    else:
        verify = _run(["bash", "-lc", verify_cmd], cwd=root)

    return {
        "branches": branches,
        "verified": target or "working tree",
        "run_ids": _run_ids_from_ticket(root),
        "verify_exit_code": verify.returncode,
        "head": _run(["git", "rev-parse", "--short", "HEAD"], cwd=root).stdout.strip(),
    }


def _run_ids_from_ticket(root: Path) -> list[str]:
    """Read run ids from the KORU-LLM-RUN notes the queue appends to the ticket.

    The previous location (``.planfile/.koru/runs``) is never written by the
    queue, so this reported an empty list even on a fully successful run.
    """
    sprint = root / ".planfile" / "sprints" / "current.yaml"
    if not sprint.is_file():
        return []
    ids: list[str] = []
    # The note is JSON embedded in YAML, so the quotes arrive escaped
    # (``run_id\": \"…\"``) — match them with or without the backslash.
    pattern = r'\\?"run_id\\?":\s*\\?"([0-9a-f]+)\\?"'
    for match in re.finditer(pattern, sprint.read_text(encoding="utf-8")):
        if match.group(1) not in ids:
            ids.append(match.group(1))
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep",
        metavar="DIR",
        help="Reuse or preserve fixture directory instead of a fresh temp dir",
    )
    args = parser.parse_args()

    _load_koru_dotenv()
    env_used = _require_llm_env()
    print("env:", json.dumps(env_used, indent=2))

    if args.keep:
        root = Path(args.keep).resolve()
        if not (root / ".git").is_dir():
            _init_fixture(root)
            _init_planfile(root)
    else:
        root = Path(tempfile.mkdtemp(prefix="koru-subactor-pilot-"))
        _init_fixture(root)
        _init_planfile(root)

    ticket = _render_ticket()
    ticket_id = _import_ticket(root, ticket)
    print(f"fixture: {root}")
    print(f"ticket: {ticket_id}")
    print(f"model(normalized): {_normalize_model(env_used['LLM_MODEL'])}")

    proc = _run_queue(root)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    evidence = _collect_evidence(root)
    print("\nevidence:", json.dumps(evidence, indent=2))

    if args.keep is None:
        print(f"(temp fixture kept for inspection: {root})", file=sys.stderr)
    return 0 if proc.returncode == 0 and "status=completed" in (proc.stdout + proc.stderr) else 1


if __name__ == "__main__":
    raise SystemExit(main())
