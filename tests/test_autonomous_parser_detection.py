"""Tests for autonomous command detection helpers."""

from koru.autonomous_parser import looks_like_autonomous_up_command


def test_looks_like_koru_auto_command():
    assert looks_like_autonomous_up_command("/usr/bin/koru auto --project .")


def test_looks_like_koru_autonomous_up_command():
    assert looks_like_autonomous_up_command("python3 -m koru.cli autonomous up")


def test_looks_like_unrelated_command():
    assert not looks_like_autonomous_up_command("python3 -m pytest -q")
