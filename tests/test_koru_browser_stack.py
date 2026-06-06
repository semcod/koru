"""Integration tests: Koru MCP + env2llm + nlp2oql + testql browser stack."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def koru_root() -> Path:
    return ROOT


def test_env2llm_refresh_includes_browser_stack(koru_root: Path) -> None:
    pytest.importorskip("env2llm")
    from env2llm.service.registry_service import RegistryService

    svc = RegistryService(koru_root, project_id="koru")
    ir = svc.refresh(write=False)
    names = {cmd.name for cmd in ir.commands}
    assert "nlp2oql_run" in names
    assert "browser_automation" in ir.capabilities


def test_nlp2oql_router_from_koru(koru_root: Path) -> None:
    pytest.importorskip("nlp2oql")
    from koruapi.nlp2oql_bridge import nlp2oql_available, nlp2oql_generate, nlp2oql_run

    if not nlp2oql_available():
        pytest.skip("nlp2oql not installed")

    gen = nlp2oql_generate("sprawdź health API", project_root=str(koru_root), validate=False)
    assert gen.get("ok") is True
    assert gen.get("oql")

    for prompt, backend in (
        ("zaloguj na blog", "curllm"),
        ("multi-step canvas extract", "nlp2cmd"),
        ("desktop list windows", "testql"),
    ):
        result = nlp2oql_run(prompt, project_root=str(koru_root), backend=backend, execute=False)
        assert result.get("backend") == backend
        assert result.get("ok") is True


def test_mcp_tools_include_nlp2oql() -> None:
    from koruapi import mcp_server_schema

    names = {tool["name"] for tool in mcp_server_schema.TOOLS}
    assert "koru_nlp2oql_generate" in names
    assert "koru_nlp2oql_run" in names


def test_testql_environment_scenario_dry_run(koru_root: Path) -> None:
    pytest.importorskip("testql")
    from testql.interpreter import OqlInterpreter
    from testql.interpreter._testtoon_parser import testtoon_to_oql

    sample = (koru_root / "../../oqlos/testql/examples/environment/complex-replay.testql.toon.yaml").resolve()
    if not sample.is_file():
        pytest.skip("testql example not present as sibling")
    source = sample.read_text(encoding="utf-8")
    parsed = testtoon_to_oql(source, str(sample))
    result = OqlInterpreter(quiet=True, dry_run=True).execute(parsed)
    assert result.ok
    assert any("CONTEXT" in step.name for step in result.steps)
