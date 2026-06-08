"""Protobuf EventStore replay."""

from dsl2coru.bus import dispatch
from dsl2coru.events import EventStore
from dsl2coru.handlers.runner import Runner


def _mock_runner(argv: list[str]) -> tuple[int, str, str]:
    return 0, "ok", ""


def test_replay_pb_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("dsl2coru.handlers.runner.default_runner", _mock_runner)
    ctx_file = tmp_path / "app.coru.less"
    ctx_file.write_text("// ctx\n", encoding="utf-8")

    dispatch("AUTO", runner=_mock_runner, default_project=str(ctx_file))

    store = EventStore(tmp_path / ".coru" / "events" / "dsl.events.pb", fmt="protobuf")
    events = store.replay_pb()
    assert len(events) >= 1
    assert events[0].command["verb"] == "AUTO"
