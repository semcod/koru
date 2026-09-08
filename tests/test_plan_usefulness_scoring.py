"""Characterize ranking weights and eligibility at the public scoring boundary."""

import pytest

from koru.autonomy.code_change_usefulness import is_useful_plan, plan_usefulness_score


@pytest.mark.parametrize(
    ('paths', 'expected'),
    [
        ([], -1.0),
        (['vendor/core.py', 'project/analysis.toon.yaml'], -1.0),
        (['core.py'], 14.5),
        (['src/core.py'], 17.5),
        (['lib/core.ts'], 17.5),
        (['pkg/src/core.rs'], 17.5),
        (['tests/core.js'], 15.5),
        (['test/core.java'], 15.5),
        (['config.yaml'], 12.0),
        (['src/style.css'], 15.0),
        (['docs/core.py'], 13.0),
        (['docs/guide.md'], 6.5),
        (['guide.MD'], 12.0),
        (['Dockerfile'], 10.5),
        (['src/core.py', 'docs/guide.md'], 17.5),
        (['src/core.py', 'src/core.py'], 24.5),
        (['./src\\core.py', 'vendor/core.py'], 17.5),
    ],
)
def test_exact_path_scores(paths, expected):
    assert plan_usefulness_score({'target': {'paths': paths}}) == expected


@pytest.mark.parametrize(
    ('metadata', 'expected'),
    [
        ({'priority': 'P0'}, 22.0),
        ({'priority': 'p1'}, 20.0),
        ({'priority': 'P2'}, 18.0),
        ({'priority': 'P3'}, 17.0),
        ({'priority': ' P0 '}, 17.5),
        ({'evidence': {'recordIds': ['INT-TODO-1']}}, 25.5),
        ({'evidence': {'recordIds': ['INT-CHANGELOG-1']}}, 14.5),
        ({'evidence': {'recordIds': ['INT-TODO-1', 'INT-CHANGELOG-1']}}, 25.5),
        ({'evidence': {'recordIds': [' INT-TODO-1', '', ' ']}}, 17.5),
        ({'evidence': {'diagnosticIds': ['', ' ']}}, 17.5),
        ({'evidence': {'diagnosticIds': [42, 'DIAG-2']}}, 18.5),
        ({'evidence': []}, 17.5),
    ],
)
def test_exact_metadata_scores(metadata, expected):
    assert plan_usefulness_score({'target': {'paths': ['src/core.py']}, **metadata}) == expected


@pytest.mark.parametrize(
    ('symbols', 'expected'),
    [([], 17.5), (['', ' '], 17.5), (['run'], 20.0), (['run'] * 6, 22.5),
     (['run'] * 8, 22.5), ([0, None, ''], 20.5)],
)
def test_symbol_bonus_and_cap(symbols, expected):
    plan = {'target': {'paths': ['src/core.py'], 'symbols': symbols}}
    assert plan_usefulness_score(plan) == expected


def test_usable_target_paths_take_precedence_over_changes():
    plan = {'target': {'paths': ['core.py']}, 'changes': [{'path': 'src/extra.py'}]}
    assert plan_usefulness_score(plan) == 14.5


@pytest.mark.parametrize('target', [None, [], {'paths': ['vendor/core.py']}])
def test_changes_supply_paths_when_target_has_none_usable(target):
    plan = {'target': target, 'changes': [None, {}, {'path': './src/core.py'}]}
    assert plan_usefulness_score(plan) == 17.5


def test_existing_file_bonus_and_eligibility_threshold(tmp_path):
    path = tmp_path / 'src' / 'core.py'
    path.parent.mkdir()
    plan = {'target': {'paths': ['src/core.py']}, 'changes': [{'path': 'src/core.py', 'action': 'create'}]}
    assert plan_usefulness_score(plan, project=tmp_path) == 17.5
    assert is_useful_plan(plan, project=tmp_path, min_score=17.5)
    assert not is_useful_plan(plan, project=tmp_path, min_score=17.51)
    path.write_text('')
    assert plan_usefulness_score(plan, project=tmp_path) == 18.0
    assert not is_useful_plan(plan, project=tmp_path)
    plan['changes'][0]['action'] = 'modify'
    assert is_useful_plan(plan, project=tmp_path, min_score=18.0)
    assert not is_useful_plan(plan, project=tmp_path, min_score=18.01)


def test_invalid_manifest_prevents_positive_score(tmp_path):
    governance = tmp_path / '.governance'
    governance.mkdir()
    (governance / 'manifest.json').write_text('{}')
    plan = {'target': {'paths': ['src/core.py']}, 'priority': 'P0'}
    assert plan_usefulness_score(plan, project=tmp_path) == -1.0
