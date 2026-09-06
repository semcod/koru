"""Quality reports distinguish failed verification from successful checks."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from koru.ci.gates import gate_commands, run_quality_gates


@pytest.mark.parametrize('failure', ['missing', 'permission', 'exit', 'unknown'])
@pytest.mark.parametrize('fail_fast', [True, False])
def test_unsuccessful_gate_fails_overall(tmp_path: Path, failure: str, fail_fast: bool) -> None:
    denied = tmp_path / 'not-executable'
    denied.write_text('not an executable')
    commands = {
        'missing': [str(tmp_path / 'missing')],
        'permission': [str(denied)],
        'exit': [sys.executable, '-c', 'raise SystemExit(3)'],
        'ok': [sys.executable, '-c', 'pass'],
    }
    with patch('koru.ci.gates.gate_commands', return_value=commands):
        result = run_quality_gates(
            tmp_path, gates=[failure, 'ok'], fail_fast=fail_fast, oom_kill_threshold_mb=0,
        )
    assert result['overall_status'] == 'failed'
    assert len(result['results']) == (1 if fail_fast else 2)
    if not fail_fast:
        assert result['results'][-1]['status'] == 'passed'


def test_report_identifies_absolute_regix_command(tmp_path: Path) -> None:
    expected = ['regix', 'gates', '--workdir', str(tmp_path)]
    assert gate_commands(tmp_path)['regix'] == expected
    with patch('koru.ci.gates.run_single_gate', return_value=(
        'passed', {'gate': 'regix', 'status': 'passed', 'issues': []},
    )):
        result = run_quality_gates(tmp_path, gates=['regix'])
    assert result['overall_status'] == 'passed'
    assert result['results'][0]['command'] == expected
