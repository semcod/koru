from __future__ import annotations

import json
import sqlite3
import sys
from types import ModuleType

from koru.model_history import append_routing_event, model_history_payload


def make_history(path, project):
    with sqlite3.connect(path) as db:
        db.executescript(
            "CREATE TABLE session(id TEXT,directory TEXT); "
        "CREATE TABLE message(id TEXT,session_id TEXT,time_created INTEGER,data TEXT);"
        )
        for sid, directory in [
            ("s1", str(project)),
            ("s2", str(project) + "-other"),
            ("s3", str(project / ".worktrees/ticket-1")),
        ]:
            db.execute("INSERT INTO session VALUES (?,?)", (sid, directory))
            data = {
                "role": "assistant",
                "providerID": "zai",
                "modelID": "glm-5.3-flash",
                "finish": "stop",
                "tokens": {"input": 10, "output": 3, "cache": {"read": 2}},
                "content": "secret prompt",
            }
            db.execute("INSERT INTO message VALUES (?,?,?,?)", ("m" + sid, sid, 1789845000000, json.dumps(data)))


def test_history_reads_real_model_metadata_without_prompts_or_other_projects(tmp_path, monkeypatch):
    monkeypatch.setattr("koru.model_history._subllm_history", lambda limit: {"status": "not_installed", "calls": []})
    path = tmp_path / "history.sqlite"
    make_history(path, tmp_path)
    before = path.read_bytes()
    result = model_history_payload(tmp_path, db_path=path)
    assert path.read_bytes() == before
    calls = result["opencode"]["calls"]
    assert {x["session_id"] for x in calls} == {"s1", "s3"}
    assert calls[0]["model"] == "glm-5.3-flash"
    assert calls[0]["input_tokens"] == 10
    assert all(x["ticket"] is None for x in calls)
    assert "secret prompt" not in json.dumps(result)


def test_absent_history_stays_absent_and_limit_is_bounded(tmp_path):
    path = tmp_path / "absent.sqlite"
    result = model_history_payload(tmp_path, limit=100000, db_path=path)
    assert result["opencode"]["status"] == "missing"
    assert result["limit"] == 200 and not path.exists()
    assert not (tmp_path / ".planfile").exists()


def test_malformed_database_returns_availability_not_sql_or_file_contents(tmp_path):
    path = tmp_path / "bad.sqlite"
    path.write_text("secret credential")
    result = model_history_payload(tmp_path, db_path=path)
    assert result["opencode"] == {"status": "unavailable", "calls": []}
    assert "credential" not in json.dumps(result)


def test_receipts_are_allowlisted_and_separate_from_actual_calls(tmp_path):
    assert append_routing_event(
        tmp_path,
        {
            "ticket": "TEST-1",
            "requested_model": "zai/glm-5.3-flash",
            "reason": "bounded_lint",
            "status": "started",
            "prompt": "private",
            "token": "secret",
        },
    )
    result = model_history_payload(tmp_path, db_path=tmp_path / "absent")
    assert result["opencode"]["calls"] == []
    assert result["decisions"][0]["requested_model"] == "zai/glm-5.3-flash"
    text = (tmp_path / ".planfile/.koru/model-routing.jsonl").read_text()
    assert "private" not in text and "secret" not in text


def test_optional_subllm_uses_producer_query_and_app_scope(tmp_path, monkeypatch):
    module = ModuleType("subllm.usage")
    seen = []

    def query(filters):
        seen.append(filters)
        return {
            "storage": "sqlite",
            "attempts": [{"application": "koru-agent", "model": "glm-5.3", "status": "success", "prompt": "secret"}],
        }

    module.query_usage = query
    monkeypatch.setitem(sys.modules, "subllm.usage", module)
    result = model_history_payload(tmp_path, limit=2, db_path=tmp_path / "absent")
    assert seen == [{"application": "koru-agent", "limit": 2}]
    assert result["subllm"]["scope"] == "koru-agent across projects"
    assert "secret" not in json.dumps(result)
