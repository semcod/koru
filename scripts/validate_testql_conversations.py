#!/usr/bin/env python3
"""Validate conversation TestQL scenarios (parse IR + dry-run when testql supports it)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCENARIO_DIR = REPO / "testql-scenarios" / "conversations"


def _format_validation_errors(path: Path, summary: str, issues: list[str]) -> list[str]:
    prefix = f"{path}:"
    if issues:
        return [f"{prefix} {issue}" for issue in issues]
    return [f"{prefix} {summary}"]


def _sdk_structural_checks(path: Path) -> list[str]:
    try:
        from nlp2dsl_sdk.conversation_testql import validate_conversation_scenario
    except ImportError:
        return _fallback_basic_checks(path)

    result = validate_conversation_scenario(path)
    if result.passed:
        return []
    return _format_validation_errors(path, result.summary, result.issues)


def _fallback_basic_checks(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if "# TYPE: conversation" not in text:
        errors.append(f"{path}: missing '# TYPE: conversation'")
    if "NLP_DSL" not in text:
        errors.append(f"{path}: missing NLP_DSL section")
    return errors


def _testql_adapter_checks(path: Path) -> list[str]:
    try:
        from testql.adapters.nlp2dsl import Nlp2DslAdapter
        from testql.conversation import ConversationRunner
    except ImportError:
        return []

    errors: list[str] = []
    adapter = Nlp2DslAdapter()
    plan = adapter.parse(path)
    errors.extend(
        f"{path}: {issue.message}"
        for issue in adapter.validate(plan)
        if issue.severity == "error"
    )
    result = ConversationRunner(
        dry_run=True,
        api_url=str(plan.config.get("nlp2dsl_base_url", "http://localhost:8080")),
    ).run(plan)
    if not result.passed:
        errors.append(f"{path}: conversation dry-run failed: {', '.join(result.findings)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Scenario files (default: all conversations/)")
    parser.add_argument("--execute-mock", action="store_true", help="Run with mock LLM (requires nlp2dsl)")
    args, _unknown = parser.parse_known_args(argv or sys.argv[1:])

    paths = [Path(p) for p in args.paths] if args.paths else sorted(SCENARIO_DIR.glob("*.testql.toon.yaml"))
    if not paths:
        print("No conversation scenarios found")
        return 0

    errors: list[str] = []
    for path in paths:
        if not path.is_file():
            errors.append(f"missing file: {path}")
            continue
        errors.extend(_sdk_structural_checks(path))
        errors.extend(_testql_adapter_checks(path))

    if args.execute_mock:
        runner = REPO / "scripts" / "run_testql_conversations.py"
        for path in paths:
            proc = subprocess.run(
                [sys.executable, str(runner), str(path)],
                cwd=REPO,
                check=False,
            )
            if proc.returncode != 0:
                errors.append(f"{path}: mock execute failed (exit {proc.returncode})")

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    print(f"Validated {len(paths)} conversation scenario(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
