"""Tests for code-change usefulness filters."""

from __future__ import annotations

import json

from koru.autonomy.code_change_usefulness import (
    is_governance_owned_path,
    is_useful_code_change_path,
    is_useful_plan,
    plan_usefulness_score,
)


def test_rejects_vendored_and_binary_paths() -> None:
    assert is_useful_code_change_path("src/foo.py")
    assert not is_useful_code_change_path(".testvenv/lib/python3.13/site-packages/x.py")
    assert not is_useful_code_change_path("node_modules/left-pad/index.js")
    assert not is_useful_code_change_path("project/compact_flow.png")
    assert not is_useful_code_change_path("project/analysis.toon.yaml")
    assert not is_useful_code_change_path("examples/*/*")


def test_rejects_governance_and_participant_paths() -> None:
    protected = (
        "AGENTS.md",
        "POLICY.md",
        "TODO.md",
        ".governance/manifest.json",
        "project/TICKETS.md",
        "project/ticket-001/README.md",
        "project/ticket-001/user-alice.md",
        "project/ticket-001/ai-codex.md",
        "project/ticket-001/ai-codex-logs.txt",
    )
    assert all(is_governance_owned_path(path) for path in protected)
    assert all(not is_useful_code_change_path(path) for path in protected)


def test_rejects_symbol_qualified_path_as_a_file_target() -> None:
    assert not is_useful_code_change_path("src/koru/scan.py::run_scan")


def test_target_manifest_governance_paths_are_protected(tmp_path) -> None:
    governance = tmp_path / ".governance"
    governance.mkdir()
    (governance / "manifest.json").write_text(
        json.dumps({"governancePaths": ["custom-policy/**"]}),
        encoding="utf-8",
    )
    assert is_governance_owned_path("custom-policy/rules.yaml", project=tmp_path)
    assert not is_useful_code_change_path(
        "custom-policy/rules.yaml",
        project=tmp_path,
    )


def test_invalid_target_manifest_fails_closed(tmp_path) -> None:
    governance = tmp_path / ".governance"
    governance.mkdir()
    (governance / "manifest.json").write_text("not json\n", encoding="utf-8")
    assert not is_useful_code_change_path("src/core.py", project=tmp_path)


def test_plan_score_prefers_source_over_docs() -> None:
    source_plan = {
        "priority": "P0",
        "target": {"paths": ["src/core.py"], "symbols": ["run"]},
        "evidence": {"recordIds": ["INT-TODO-aaaaaaaaaaaaaaaaaaaa"], "diagnosticIds": ["DIAG-1"]},
    }
    docs_plan = {
        "priority": "P3",
        "target": {"paths": ["docs/readme.md"], "symbols": []},
        "evidence": {"recordIds": ["INT-CHANGELOG-bbbbbbbbbbbbbbbbbbbb"], "diagnosticIds": ["DIAG-2"]},
    }
    assert plan_usefulness_score(source_plan) > plan_usefulness_score(docs_plan)
    assert is_useful_plan(source_plan)
    assert not is_useful_plan(docs_plan, min_score=-100)


def test_changelog_plus_todo_remains_autonomous() -> None:
    plan = {
        "priority": "P1",
        "target": {"paths": ["src/core.py"], "symbols": ["run"]},
        "evidence": {
            "recordIds": [
                "INT-CHANGELOG-bbbbbbbbbbbbbbbbbbbb",
                "INT-TODO-aaaaaaaaaaaaaaaaaaaa",
            ],
            "diagnosticIds": ["DIAG-1"],
        },
    }
    assert is_useful_plan(plan)


def test_high_risk_and_missing_modify_targets_require_review(tmp_path) -> None:
    existing = tmp_path / "src" / "core.py"
    existing.parent.mkdir()
    existing.write_text("def run(): pass\n", encoding="utf-8")
    base = {
        "priority": "P2",
        "target": {"paths": ["src/core.py"], "symbols": ["run"]},
        "evidence": {
            "recordIds": ["INT-TODO-aaaaaaaaaaaaaaaaaaaa"],
            "diagnosticIds": ["DIAG-1"],
        },
        "risk": {"level": "low"},
    }
    assert is_useful_plan(base, project=tmp_path)
    assert not is_useful_plan({**base, "risk": {"level": "high"}}, project=tmp_path)
    missing = {**base, "target": {"paths": ["src/missing.py"], "symbols": []}}
    assert not is_useful_plan(missing, project=tmp_path)


def test_explicit_create_plan_is_useful_only_while_target_is_absent(tmp_path) -> None:
    plan = {
        "priority": "P1",
        "target": {"paths": ["src/new_module.py"], "symbols": []},
        "changes": [
            {
                "path": "src/new_module.py",
                "action": "create",
                "rationale": "Add the declared module",
            }
        ],
        "evidence": {
            "recordIds": ["INT-TODO-aaaaaaaaaaaaaaaaaaaa"],
            "diagnosticIds": ["DIAG-1"],
        },
        "risk": {"level": "low"},
    }
    assert is_useful_plan(plan, project=tmp_path)
    target = tmp_path / "src" / "new_module.py"
    target.parent.mkdir()
    target.write_text("# existing\n", encoding="utf-8")
    assert not is_useful_plan(plan, project=tmp_path)
