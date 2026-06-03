from __future__ import annotations

from pathlib import Path

from koruapi.runtime_insights import collect_runtime_insights


def _stub_process_sources(monkeypatch) -> None:
    monkeypatch.setattr("koruapi.runtime_insights.detect_running_ides", lambda: [])
    monkeypatch.setattr(
        "koruapi.runtime_insights.find_existing_autonomous_processes",
        lambda _p: [],
    )
    monkeypatch.setattr("koruapi.runtime_insights.find_existing_wup_processes", lambda _p: [])


def test_collect_runtime_insights_summarizes_processes(monkeypatch) -> None:
    monkeypatch.setattr(
        "koruapi.runtime_insights._run_ps",
        lambda: [
            {
                "pid": 10,
                "pcpu": 12.5,
                "pmem": 1.2,
                "rss_kb": 50000,
                "rss_mb": 48.8,
                "etime": "00:10",
                "comm": "python",
                "args": "python -m koru.cli autonomous up /tmp/demo",
            },
            {
                "pid": 20,
                "pcpu": 8.0,
                "pmem": 0.9,
                "rss_kb": 35000,
                "rss_mb": 34.2,
                "etime": "00:20",
                "comm": "node",
                "args": "playwright chrome-headless-shell",
            },
        ],
    )
    _stub_process_sources(monkeypatch)

    data = collect_runtime_insights(Path("/tmp/demo"))

    assert data["summary"]["active_tools"] == 2
    assert data["active_tools"][0]["id"] == "koru"
    assert data["active_tools"][1]["id"] == "playwright"
    assert data["top_processes"][0]["pid"] == 10


def test_collect_runtime_insights_includes_detected_ides(monkeypatch) -> None:
    class _Ide:
        def to_dict(self) -> dict[str, object]:
            return {"id": "vscode", "label": "VS Code", "pid": 123}

    monkeypatch.setattr("koruapi.runtime_insights._run_ps", lambda: [])
    monkeypatch.setattr("koruapi.runtime_insights.detect_running_ides", lambda: [_Ide()])
    monkeypatch.setattr(
        "koruapi.runtime_insights.find_existing_autonomous_processes",
        lambda _p: [],
    )
    monkeypatch.setattr("koruapi.runtime_insights.find_existing_wup_processes", lambda _p: [])

    data = collect_runtime_insights(Path("/tmp/demo"))

    assert data["summary"]["running_ides"] == 1
    assert data["running_ides"][0]["id"] == "vscode"


def test_collect_runtime_insights_uses_sllm_shell_patterns(monkeypatch) -> None:
    monkeypatch.setattr(
        "koruapi.runtime_insights._run_ps",
        lambda: [
            {
                "pid": 30,
                "pcpu": 5.0,
                "pmem": 0.4,
                "rss_kb": 24000,
                "rss_mb": 23.4,
                "etime": "00:05",
                "comm": "codex",
                "args": "codex",
            },
        ],
    )
    monkeypatch.setattr(
        "koruapi.runtime_insights.shell_agent_process_patterns",
        lambda: (("codex", "Codex CLI", ("codex",)),),
    )
    _stub_process_sources(monkeypatch)

    data = collect_runtime_insights(Path("/tmp/demo"))

    assert data["active_tools"][0]["id"] == "codex"
    assert data["active_tools"][0]["label"] == "Codex CLI"
