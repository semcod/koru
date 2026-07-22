from __future__ import annotations

from types import SimpleNamespace

from koruapi import testql_bridge
from koruapi.mcp_server_testql import tool_testql_list_scenarios, tool_testql_run_scenario


def test_testql_list_without_package(monkeypatch) -> None:
    monkeypatch.setattr(testql_bridge, "_TESTQL_AVAILABLE", False)
    payload = testql_bridge.testql_list_scenarios(project_root=".")
    assert payload["ok"] is False


def test_testql_run_uses_public_hashed_verification_contract(monkeypatch, tmp_path) -> None:
    calls: list[object] = []

    class FakeRequest:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    class FakeResult:
        def to_dict(self) -> dict:
            return {
                "schema": "testql.verification-result.v1",
                "ok": True,
                "files": 1,
                "runs": [{"ok": True}],
                "dry_run": True,
                "request_hash": "0" * 64,
                "result_hash": "1" * 64,
            }

    def fake_run(request):
        calls.append(request)
        return FakeResult()

    api = SimpleNamespace(VerificationRequest=FakeRequest, run_verification=fake_run)
    monkeypatch.setattr(testql_bridge, "_TESTQL_AVAILABLE", True)
    monkeypatch.setattr(testql_bridge, "_TESTQL_API", api)

    payload = testql_bridge.testql_run_scenario(
        "checks/*.testql.toon.yaml",
        project_root=str(tmp_path),
    )

    assert payload["schema"] == "testql.verification-result.v1"
    assert len(payload["request_hash"]) == len(payload["result_hash"]) == 64
    assert len(calls) == 1
    assert calls[0].kwargs["file_specs"] == ("checks/*.testql.toon.yaml",)
    assert calls[0].kwargs["project_dir"] == tmp_path.resolve()


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
