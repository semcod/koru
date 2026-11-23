from contextlib import closing
import sqlite3
from subprocess import CompletedProcess

import yaml

from koru import pytest_incidents as incidents
from koru import scan
from koru.runtime import runtime_dir


def probe(project, names=(), *, code=None, apply=True):
    project.joinpath("tests").mkdir(exist_ok=True)
    raw = "\n".join(f"E   ModuleNotFoundError: No module named '{n}'" for n in names)
    return scan.scan_pytest_collect(
        project, runner=lambda cmd, path: CompletedProcess(cmd, code if code is not None else 2 if names else 0, raw, ""),
        record_incidents=apply,
    )


def test_archived_failure_bound_to_module_and_verified_recovery(tmp_path, monkeypatch):
    monkeypatch.delenv("URTLOG_STATE_DIR", raising=False)
    monkeypatch.setattr("koru.queue.planfile_sync.sync_planfile_integrations", lambda p: None)
    sprints = tmp_path / ".planfile/sprints"
    sprints.mkdir(parents=True)
    # Exercise the production scanner's default native ticket intake and archive payload.
    first = probe(tmp_path, ["tenacity"])
    outcome = scan._apply_scan_suggestions(tmp_path, first, source="koru-scan", runner=None)
    assert outcome.applied == [first[0].title]
    current = sprints / "current.yaml"
    data = yaml.safe_load(current.read_text())
    tickets = data["sprint"]["tickets"]
    ticket = next(iter(tickets.values()))
    assert ticket["inputs"]["expect_files_changed"] is False
    ticket["status"] = "blocked"
    (sprints / "history-regression.yaml").write_text(yaml.safe_dump(data))
    current.write_text(yaml.safe_dump({"sprint": {"tickets": {}}}))
    names = ["tenacity", "aiohttp"]
    more = probe(tmp_path, names)
    outcome = scan._apply_scan_suggestions(tmp_path, more, source="koru-scan", runner=None)
    assert first[0].title in outcome.skipped_as_duplicate
    assert len(outcome.applied) == 1 and "aiohttp" in outcome.applied[0]
    assert probe(tmp_path, (), code=5) == []
    assert probe(tmp_path, ["tenacity"])[0].source_context == first[0].source_context
    assert probe(tmp_path) == []
    again = probe(tmp_path, ["tenacity"])
    assert again[0].source_context != first[0].source_context
    outcome = scan._apply_scan_suggestions(tmp_path, again, source="koru-scan", runner=None)
    assert outcome.applied == [again[0].title]


def test_legacy_archive_and_read_only_preview(tmp_path, monkeypatch):
    monkeypatch.delenv("URTLOG_STATE_DIR", raising=False)
    sprints = tmp_path / ".planfile/sprints"
    sprints.mkdir(parents=True)
    old = {"status": "blocked", "source": {"tool": "koru-scan", "context": {
        "signal": "pytest_collect", "input": "trace\n    ModuleNotFoundError: No module named 'tenacity'",
    }}}
    (sprints / "history-old.yaml").write_text(yaml.safe_dump({"sprint": {"tickets": {"PLF-1": old}}}))
    f = probe(tmp_path, ["tenacity"], apply=False)[0]
    assert not runtime_dir(tmp_path).exists()
    keys = scan._existing_scan_titles(tmp_path, source="koru-scan")
    assert scan._scan_duplicate_skip(f, keys, source="koru-scan")[0] == "duplicate_pytest_incident"
    assert scan._scan_duplicate_skip(f, keys, source="different") is None


def test_outbox_tracks_only_transitions_and_survives_unavailable_consumer(tmp_path, monkeypatch):
    monkeypatch.setenv("URTLOG_STATE_DIR", str(tmp_path / "urtlog"))
    monkeypatch.setattr(incidents, "_repository", lambda p: "semcod/nxdo")
    monkeypatch.setattr(incidents, "_deliver", lambda *args: None)
    for start, names, success in [(10, {"tenacity"}, False), (11, {"tenacity"}, False), (12, set(), True)]:
        incidents.record_probe(tmp_path, names, success=success, started_ns=start, output="original evidence")
    assert incidents.record_probe(tmp_path, {"tenacity"}, success=False, started_ns=9, output="late result") is None
    with closing(sqlite3.connect(runtime_dir(tmp_path) / "pytest-incidents.sqlite3")) as conn:
        import json
        events = [json.loads(row[0]) for row in conn.execute("SELECT body FROM outbox ORDER BY seq")]
    assert [e["outcome"] for e in events] == ["failure", "success"]
    assert all(e["failure_code"] == "missing-dependency.tenacity" for e in events)


def test_configuring_consumer_drains_previously_observed_first_failure(tmp_path, monkeypatch):
    import sys
    from types import ModuleType
    monkeypatch.delenv("URTLOG_STATE_DIR", raising=False)
    monkeypatch.setattr(incidents, "_repository", lambda p: "semcod/nxdo")
    probe(tmp_path, ["tenacity"])
    calls = []
    class Store:
        def __init__(self, state):
            self.state = state
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    def observe(store, event, *, principal):
        calls.append((event["source_event_id"], event["repository"], principal))
        return {"advice": "received"}
    facts = ModuleType("urtlog.facts")
    facts.observe_check = observe
    storage = ModuleType("urtlog.store")
    storage.UrtLogStore = Store
    monkeypatch.setitem(sys.modules, "urtlog.facts", facts)
    monkeypatch.setitem(sys.modules, "urtlog.store", storage)
    monkeypatch.setenv("URTLOG_STATE_DIR", str(tmp_path / "urtlog"))
    probe(tmp_path, ["tenacity"])
    probe(tmp_path, ["tenacity"])
    assert len(calls) == 1 and calls[0][1:] == ("semcod/nxdo", "koru")
