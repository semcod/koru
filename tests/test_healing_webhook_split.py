from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _CounterHandle:
    def __init__(self) -> None:
        self.calls = 0

    def inc(self) -> None:
        self.calls += 1


class _Counter:
    def __init__(self) -> None:
        self.handles: list[_CounterHandle] = []

    def labels(self, **_kwargs: Any) -> _CounterHandle:
        handle = _CounterHandle()
        self.handles.append(handle)
        return handle


class _Log:
    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return


def test_route_alertmanager_payload_routes_and_tickets() -> None:
    module = _load_module(
        "healing_app_command_routing",
        Path("services/healing-webhook/app_command_routing.py"),
    )

    def resolve_strategy(name: str):
        def _strategy(component: str, detail: dict[str, Any]) -> dict[str, Any]:
            return {"strategy": name, "component": component, "detail_keys": sorted(detail.keys())}

        return _strategy, name

    ticket_calls: list[dict[str, Any]] = []

    def create_ticket(alert: dict[str, Any]) -> dict[str, Any]:
        ticket_calls.append(alert)
        return {"ticket_id": "PLF-100"}

    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "severity": "critical",
                    "component": "api",
                    "healing_strategy": "redup_check",
                    "alertname": "BudgetBreach",
                },
                "annotations": {"summary": "dup budget breach"},
            },
            {
                "status": "resolved",
                "labels": {
                    "severity": "info",
                    "component": "api",
                    "healing_strategy": "redsl_gate",
                    "alertname": "Cleared",
                },
                "annotations": {},
            },
        ]
    }

    out = module.route_alertmanager_payload(
        payload,
        resolve_strategy=resolve_strategy,
        create_planfile_ticket=create_ticket,
        alerts_counter=_Counter(),
        log=_Log(),
    )

    assert out["received"] == 2
    assert out["results"][0]["ticket"] == {"ticket_id": "PLF-100"}
    assert out["results"][1]["ticket"] == {"skipped": "severity_below_threshold"}
    assert len(ticket_calls) == 1


def test_route_probe_failure_payload_selects_strategy_and_builds_ticket() -> None:
    module = _load_module(
        "healing_app_command_routing",
        Path("services/healing-webhook/app_command_routing.py"),
    )

    chosen: list[str] = []

    def heal_improve(_component: str, _detail: dict[str, Any]) -> dict[str, Any]:
        chosen.append("improve")
        return {"action": "redsl_improve", "outcome": "success"}

    def heal_gate(_component: str, _detail: dict[str, Any]) -> dict[str, Any]:
        chosen.append("gate")
        return {"action": "redsl_gate", "outcome": "success"}

    synthetic: list[dict[str, Any]] = []

    def create_ticket(alert: dict[str, Any]) -> dict[str, Any]:
        synthetic.append(alert)
        return {"ticket_id": "PLF-101"}

    payload = {
        "source": "watchdog",
        "total": 4,
        "failures": [
            {"endpoint": "https://svc-a"},
            {"endpoint": "https://svc-b"},
            {"endpoint": "https://svc-c"},
        ],
    }

    out = module.route_probe_failure_payload(
        payload,
        heal_redsl_improve=heal_improve,
        heal_redsl_gate=heal_gate,
        create_planfile_ticket=create_ticket,
        alerts_counter=_Counter(),
        enable_llm_autofix=True,
        log=_Log(),
    )

    assert out["failures"] == 3
    assert out["ticket"] == {"ticket_id": "PLF-101"}
    assert chosen == ["improve"]
    assert synthetic[0]["labels"]["severity"] == "critical"


def test_bootstrap_wires_expected_routes() -> None:
    pytest.importorskip("fastapi")
    module = _load_module(
        "healing_app_bootstrap",
        Path("services/healing-webhook/app_bootstrap.py"),
    )
    app = module.create_webhook_app(title="x", version="1")

    async def _noop_async(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {}

    def _noop_sync(*_args: Any, **_kwargs: Any):
        return {}

    module.wire_routes(
        app,
        healthz_handler=_noop_sync,
        metrics_handler=_noop_sync,
        history_handler=_noop_sync,
        alertmanager_handler=_noop_async,
        probe_failure_handler=_noop_async,
        tickets_handler=_noop_sync,
    )

    route_paths = {route.path for route in app.routes}
    for path in {"/healthz", "/metrics", "/history", "/alertmanager", "/probe-failure", "/tickets"}:
        assert path in route_paths


def test_run_docker_uses_expected_command(monkeypatch) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("prometheus_client")
    module = _load_module(
        "healing_app_main",
        Path("services/healing-webhook/app.py"),
    )
    captured: list[list[str]] = []

    def fake_run(command, **_kwargs):  # noqa: ANN001
        captured.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    code, out, err = module._run_docker("image:tag", ["tool", "arg"], timeout=7)

    assert code == 0
    assert out == "ok"
    assert err == ""
    assert captured == [
        [
            "docker",
            "run",
            "--rm",
            "--network=c2004-quality-net",
            "-v",
            f"{module.REPO_PATH}:/mnt/project:rw",
            "-w",
            "/mnt/project",
            "image:tag",
            "tool",
            "arg",
        ]
    ]
