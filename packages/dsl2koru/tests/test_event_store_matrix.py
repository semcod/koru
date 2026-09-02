from pathlib import Path

import pytest
from dsl2koru.events import EventStore


@pytest.mark.parametrize(
    ("factory", "namespace", "suffix", "fmt"),
    [
        ("project", ".koru", "dsl.events.pb", "protobuf"),
        ("project-json", ".koru", "dsl.events.jsonl", "jsonl"),
        ("default", ".coru", "dsl.events.pb", "protobuf"),
        ("default-json", ".coru", "dsl.events.jsonl", "jsonl"),
    ],
)
def test_location_matrix(tmp_path, factory, namespace, suffix, fmt) -> None:
    if factory.startswith("project"):
        store = EventStore.for_project(tmp_path, prefer_pb=not factory.endswith("json"))
    else:
        store = EventStore.for_default(
            str(tmp_path / "workflow.plan"),
            prefer_pb=not factory.endswith("json"),
        )

    assert store.path == tmp_path / namespace / "events" / suffix
    assert store.fmt == fmt


@pytest.mark.parametrize("fmt", ["protobuf", "jsonl"])
def test_multi_record_replay_preserves_order(tmp_path, fmt) -> None:
    suffix = ".pb" if fmt == "protobuf" else ".jsonl"
    store = EventStore(tmp_path / f"events{suffix}", fmt=fmt)

    first = store.append_command({"verb": "STATUS"}, {"ok": True, "verb": "STATUS"})
    second = store.append_command({"verb": "AUTO"}, {"ok": False, "verb": "AUTO"})

    events = store.read_all()
    assert [event.id for event in events] == [first, second]
    assert [event.command["verb"] for event in events] == ["STATUS", "AUTO"]
    assert [event.result["ok"] for event in events] == [True, False]
    assert store.replay() == events


def test_protobuf_replay_ignores_incomplete_header_tail(tmp_path) -> None:
    store = EventStore(tmp_path / "events.pb", fmt="protobuf")
    event_id = store.append_command({"verb": "STATUS"}, {"ok": True, "verb": "STATUS"})
    with store.path.open("ab") as stream:
        stream.write(b"\x00\x00")

    assert [event.id for event in store.read_all()] == [event_id]
    assert [event.id for event in store.replay_pb()] == [event_id]


def test_missing_store_replays_empty(tmp_path) -> None:
    store = EventStore(Path(tmp_path, "missing.pb"), fmt="protobuf")

    assert store.read_all() == []
    assert store.replay_pb() == []
    assert store.replay() == []
