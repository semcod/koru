from __future__ import annotations

from koru.autonomous_process_guard import _confirm_replace_response


def test_confirm_replace_response_accepts_localized_yes_values() -> None:
    assert _confirm_replace_response("y")
    assert _confirm_replace_response("YES\n")
    assert _confirm_replace_response("tak")
    assert _confirm_replace_response(" t ")


def test_confirm_replace_response_rejects_empty_and_no_values() -> None:
    assert not _confirm_replace_response("")
    assert not _confirm_replace_response("n")
    assert not _confirm_replace_response("nie")
