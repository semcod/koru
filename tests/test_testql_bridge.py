from __future__ import annotations

from koruapi import testql_bridge
from koruapi.mcp_server_testql import tool_testql_list_scenarios, tool_testql_run_scenario


def test_testql_list_without_package(monkeypatch) -> None:
    monkeypatch.setattr(testql_bridge, "_TESTQL_AVAILABLE", False)
    payload = testql_bridge.testql_list_scenarios(project_root=".")
    assert payload["ok"] is False


def test_testql_mcp_tools(tmp_path) -> None:
    if not testql_bridge.testql_available():
        payload = tool_testql_list_scenarios({"project_root": str(tmp_path)})
        assert payload["ok"] is False
        return

    scenario = tmp_path / "smoke.testql.toon.yaml"
    scenario.write_text(
        "# TYPE: gui\nWAIT[1]{ms}:\n  10\n",
        encoding="utf-8",
    )
    listed = tool_testql_list_scenarios({"project_root": str(tmp_path)})
    assert listed.get("ok") is True
    assert listed.get("scenario_count", 0) >= 1

    ran = tool_testql_run_scenario(
        {
            "file_spec": str(scenario),
            "project_root": str(tmp_path),
            "dry_run": True,
        }
    )
    assert ran.get("ok") is True
    assert ran.get("runs")
