"""Tests for autonomous command detection helpers."""

from koru.autonomous_parser import looks_like_autonomous_up_command


def test_looks_like_koru_auto_command():
    assert looks_like_autonomous_up_command("/usr/bin/koru auto --project .")


def test_looks_like_top_level_koru_auto_alias():
    assert looks_like_autonomous_up_command("/home/tom/project/.venv/bin/koru -a --project .")


def test_looks_like_koru_autonomous_up_command():
    assert looks_like_autonomous_up_command("python3 -m koru.cli autonomous up")


def test_looks_like_unrelated_command():
    assert not looks_like_autonomous_up_command("python3 -m pytest -q")


def test_does_not_match_autonomous_status_command():
    assert not looks_like_autonomous_up_command("koru autonomous status --project .")


def test_does_not_match_shell_text_that_mentions_koru_auto():
    command = "/bin/bash -c \"echo 'koru -a and koru autonomous are docs text only'\""
    assert not looks_like_autonomous_up_command(command)
