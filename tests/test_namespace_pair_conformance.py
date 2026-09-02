"""Cross-family conformance for the one-release Coru compatibility surface."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE_PAIRS = (
    ("cli2coru", "cli2koru"),
    ("dsl2coru", "dsl2koru"),
    ("mcp2coru", "mcp2koru"),
    ("nlp2coru", "nlp2koru"),
    ("rest2coru", "rest2koru"),
    ("uri2coru", "uri2koru"),
)
SOURCE_ROOTS = tuple(ROOT / "packages" / namespace / "src" for pair in NAMESPACE_PAIRS for namespace in pair)


def _run_isolated(script: str) -> subprocess.CompletedProcess[str]:
    pythonpath = os.pathsep.join(map(str, SOURCE_ROOTS))
    environment = {**os.environ, "PYTHONPATH": pythonpath}
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(("legacy", "canonical"), NAMESPACE_PAIRS)
def test_legacy_command_warns_and_aliases_canonical_entrypoint(legacy: str, canonical: str) -> None:
    script = f"""
import importlib
import warnings

with warnings.catch_warnings(record=True) as seen:
    warnings.simplefilter("always")
    importlib.import_module("{legacy}")

assert any(item.category is DeprecationWarning for item in seen)
legacy_cli = importlib.import_module("{legacy}.cli")
canonical_cli = importlib.import_module("{canonical}.cli")
assert legacy_cli.main is canonical_cli.main
"""
    completed = _run_isolated(script)

    assert completed.returncode == 0, completed.stderr


def test_protobuf_text_helper_is_one_alias_with_both_context_dialects() -> None:
    script = """
from dsl2coru.pb_codec import encode_text_to_protobuf as legacy_encode
from dsl2koru.pb_codec import decode_protobuf, encode_text_to_protobuf

assert legacy_encode is encode_text_to_protobuf
compatibility = decode_protobuf(encode_text_to_protobuf("ENV", default_file="compat.env"))
canonical = decode_protobuf(encode_text_to_protobuf("QUERY_REPAIR_HISTORY", default_project="project-root"))
assert compatibility["file"] == "compat.env"
assert canonical["project"] == "project-root"
"""
    completed = _run_isolated(script)

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("legacy", [pair[0] for pair in NAMESPACE_PAIRS])
def test_legacy_production_modules_define_no_behavior(legacy: str) -> None:
    source_root = ROOT / "packages" / legacy / "src" / legacy
    forbidden: list[str] = []

    for path in source_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)):
                forbidden.append(f"{path.relative_to(ROOT)}:{node.lineno}:{node.name}")
            elif isinstance(node, ast.FunctionDef) and node.name != "__getattr__":
                forbidden.append(f"{path.relative_to(ROOT)}:{node.lineno}:{node.name}")

    assert forbidden == []
