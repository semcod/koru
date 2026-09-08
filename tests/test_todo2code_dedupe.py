"""Characterize the identities preventing duplicate discovery tickets."""

from __future__ import annotations

import pytest
import yaml

from koru.autonomy import todo2code_discovery as discovery


def _write_sprint(project, data, name="current"):
    directory = project / ".planfile/sprints"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


@pytest.mark.parametrize("data", [None, [], "bad", {}, {"sprint": []}, {"sprint": {"tickets": []}}])
def test_missing_ticket_mapping_has_no_identities(tmp_path, data):
    _write_sprint(tmp_path, data)
    assert discovery._existing_todo2code_keys(tmp_path) == (set(), set())


def test_missing_or_unreadable_yaml_is_best_effort(tmp_path):
    assert discovery._existing_todo2code_keys(tmp_path) == (set(), set())
    path = _write_sprint(tmp_path, {})
    path.write_text("sprint: [unterminated")
    assert discovery._existing_todo2code_keys(tmp_path) == (set(), set())


def test_collects_distinct_key_and_title_identities_from_named_sprint(tmp_path):
    tickets = {
        "prefixed": {"name": " [todo2code] Task ", "files": [" src/a.py ", "", "src/a.py"]},
        "tagged": {
            "name": "Task",
            "files": ["src/b.py"],
            "source": {"tool": discovery.DEFAULT_SOURCE, "context": {"dedupe_key": " todo2code:plan:1 "}},
        },
        "key_only": {"name": "Unrelated", "source": {"context": {"dedupe_key": "todo2code:plan:2"}}},
        "foreign": {"name": "Other", "source": {"context": {"dedupe_key": "other:1"}}},
        "invalid": None,
    }
    _write_sprint(tmp_path, {"sprint": {"tickets": tickets}}, name="next")
    assert discovery._existing_todo2code_keys(tmp_path) == (set(), set())
    assert discovery._existing_todo2code_keys(tmp_path, sprint="next") == (
        {"todo2code:plan:1", "todo2code:plan:2"},
        {("[todo2code] Task", (" src/a.py ", "src/a.py")), ("Task", ("src/b.py",))},
    )


@pytest.mark.parametrize("context", [None, [], "bad", 7])
def test_source_tag_requires_mapping_context_but_prefix_does_not(tmp_path, context):
    source = {"tool": discovery.DEFAULT_SOURCE, "context": context}
    _write_sprint(
        tmp_path,
        {
            "sprint": {
                "tickets": {
                    "a": {"name": "Task", "source": source},
                    "b": {"name": "[todo2code] Task", "source": source},
                }
            }
        },
    )
    assert discovery._existing_todo2code_keys(tmp_path) == (set(), {("[todo2code] Task", ())})


def test_file_order_and_duplicates_remain_part_of_identity(tmp_path):
    _write_sprint(
        tmp_path,
        {
            "sprint": {
                "tickets": {
                    "a": {"name": "[todo2code] Task", "files": ["a.py", "b.py"]},
                    "b": {"name": "[todo2code] Task", "files": ["b.py", "a.py"]},
                    "c": {"name": "[todo2code] Task", "files": ["a.py", "a.py"]},
                }
            }
        },
    )
    assert discovery._existing_todo2code_keys(tmp_path) == (
        set(),
        {
            ("[todo2code] Task", ("a.py", "b.py")),
            ("[todo2code] Task", ("b.py", "a.py")),
            ("[todo2code] Task", ("a.py", "a.py")),
        },
    )


def test_invalid_ticket_files_are_not_swallowed_as_yaml_failure(tmp_path):
    _write_sprint(tmp_path, {"sprint": {"tickets": {"a": {"files": 7}}}})
    with pytest.raises(TypeError):
        discovery._existing_todo2code_keys(tmp_path)
