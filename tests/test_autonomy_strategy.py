from __future__ import annotations

from pathlib import Path

import yaml

from koru.autonomy_strategy import (
    build_strategy_heuristics,
    build_strategy_update_prompt,
    ensure_autonomy_strategy_config,
    load_autonomy_strategy,
)


def test_ensure_autonomy_strategy_creates_koru_yaml(tmp_path: Path) -> None:
    result = ensure_autonomy_strategy_config(tmp_path)

    assert result.created_koru_yaml is True
    assert result.strategy_id == "accordion_detail_to_general"
    strategy = load_autonomy_strategy(tmp_path)
    assert strategy is not None
    assert strategy["source_of_truth"] == "planfile"
    assert strategy["idle_discovery"]["duplicate_cooldown_behavior"] == (
        "continue_to_general_discovery"
    )
    assert strategy["idle_discovery"]["ide_follow_up"]["enabled"] is True
    assert (
        strategy["idle_discovery"]["ide_follow_up"]["workflow"]
        == "standardized_project_discovery_ticket"
    )
    assert "Co jeszcze zostalo do wykonania?" in strategy["idle_discovery"]["ide_follow_up"]["prompt"]


def test_ensure_autonomy_strategy_appends_to_existing_yaml_without_autonomy(
    tmp_path: Path,
) -> None:
    path = tmp_path / "koru.yaml"
    path.write_text("schema: '1.0'\nproject: kept\nwhen: {}\n", encoding="utf-8")

    result = ensure_autonomy_strategy_config(tmp_path)

    assert result.created_koru_yaml is False
    assert result.added_strategy is True
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["project"] == "kept"
    assert data["autonomy"]["strategy"]["id"] == "accordion_detail_to_general"


def test_strategy_prompt_mentions_editable_yaml_and_heuristics(tmp_path: Path) -> None:
    ensure_autonomy_strategy_config(tmp_path)

    prompt = build_strategy_update_prompt(tmp_path)

    assert "autonomy.strategy" in prompt
    assert "Planfile as the source of truth" in prompt
    assert "Heuristic project report" in prompt
    assert "ide_command_api" in prompt


def test_strategy_heuristics_reports_semcod_tools(tmp_path: Path) -> None:
    report = build_strategy_heuristics(tmp_path)

    assert report["project"] == str(tmp_path.resolve())
    assert "semcod_tools" in report
    assert "ide_command_api" in report
    assert "cursor" in report["ide_command_api"]["ides"]
    assert "zed" in report["ide_command_api"]["ides"]
    assert "recommendations" in report
