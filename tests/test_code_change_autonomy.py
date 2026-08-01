"""Tests for autonomous code-change orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from koru.autonomy import code_change_autonomy as cca


def test_patch_is_fully_diffed() -> None:
    assert cca._patch_is_fully_diffed(
        {
            "edits": [
                {
                    "path": "src/a.py",
                    "unifiedDiff": (
                        "diff --git a/src/a.py b/src/a.py\n"
                        "--- a/src/a.py\n+++ b/src/a.py\n"
                        "@@ -1 +1 @@\n-a\n+b\n"
                    ),
                }
            ]
        }
    )
    assert not cca._patch_is_fully_diffed(
        {"edits": [{"path": "src/a.py", "unifiedDiff": None}]}
    )
    assert not cca._patch_is_fully_diffed(
        {"edits": [{"path": ".testvenv/x.py", "unifiedDiff": "x"}]}
    )


def test_apply_ready_skips_instruction_only(tmp_path: Path, monkeypatch) -> None:
    runs = tmp_path / ".intent" / "runs" / "r1"
    runs.mkdir(parents=True)
    (runs / "code-change-source-patches.json").write_text(
        json.dumps(
            {
                "patches": [
                    {
                        "id": "SP-1",
                        "patchHash": "a" * 64,
                        "edits": [{"path": "src/a.py", "unifiedDiff": None}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_TODO2CODE_OUT", ".intent")
    applied, skipped = cca.apply_ready_source_patches(tmp_path)
    assert applied == []
    assert skipped and "instruction-only" in skipped[0]


def test_apply_ready_never_self_approves_fully_diffed_patch(
    tmp_path: Path, monkeypatch
) -> None:
    runs = tmp_path / ".intent" / "runs" / "r1"
    runs.mkdir(parents=True)
    (runs / "code-change-source-patches.json").write_text(
        json.dumps(
            {
                "patches": [
                    {
                        "id": "SP-1",
                        "patchHash": "a" * 64,
                        "edits": [
                            {
                                "path": "src/a.py",
                                "unifiedDiff": "diff --git a/src/a.py b/src/a.py\n",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_TODO2CODE_OUT", ".intent")
    applied, skipped = cca.apply_ready_source_patches(tmp_path)
    assert applied == []
    assert skipped and "manifest transaction" in skipped[0]


def test_autonomy_disabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KORU_CODE_CHANGE_AUTONOMY", "0")
    outcome = cca.run_code_change_autonomy(tmp_path)
    assert outcome.ran is False


def test_human_ticket_promotion_requires_explicit_contract(tmp_path: Path, monkeypatch) -> None:
    import yaml

    sprint = tmp_path / ".planfile" / "sprints" / "current.yaml"
    sprint.parent.mkdir(parents=True)
    sprint.write_text(
        yaml.safe_dump(
            {
                "sprint": {
                    "tickets": {
                        "T-1": {
                            "name": "[todo2code] fix",
                            "status": "open",
                            "files": ["src/a.py"],
                            "executor": {"kind": "human", "mode": "interactive"},
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("KORU_TODO2CODE_LLM_EXECUTOR", raising=False)
    monkeypatch.delenv("KORU_TODO2CODE_CONTRACT", raising=False)
    assert cca._promote_todo2code_tickets_to_llm(tmp_path) == 0

    monkeypatch.setenv("KORU_TODO2CODE_LLM_EXECUTOR", "1")
    monkeypatch.setenv("KORU_TODO2CODE_CONTRACT", "todo2code-r1")
    assert cca._promote_todo2code_tickets_to_llm(tmp_path) == 1
    ticket = yaml.safe_load(sprint.read_text(encoding="utf-8"))["sprint"]["tickets"]["T-1"]
    assert ticket["executor"] == {"kind": "llm", "mode": "automatic"}
    assert ticket["inputs"]["contract"] == "todo2code-r1"
