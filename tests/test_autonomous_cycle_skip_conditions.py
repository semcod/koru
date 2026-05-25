from __future__ import annotations

from koru.autonomous_cycle_skip_conditions import _add_label_to_ticket_yaml_text


def test_add_label_to_ticket_yaml_text_adds_missing_label_block() -> None:
    text = """sprint:
  tickets:
    STARTER-268:
      name: Refactor helper
"""

    updated = _add_label_to_ticket_yaml_text(text, "STARTER-268", "llm-ready")

    assert updated is not None
    assert "      labels:\n      - llm-ready\n" in updated


def test_add_label_to_ticket_yaml_text_expands_inline_labels_once() -> None:
    text = """sprint:
  tickets:
    STARTER-268:
      labels: [code2llm, refactor]
      name: Refactor helper
"""

    updated = _add_label_to_ticket_yaml_text(text, "STARTER-268", "llm-ready")
    updated_again = _add_label_to_ticket_yaml_text(updated or "", "STARTER-268", "llm-ready")

    assert updated == updated_again
    expected = "      labels:\n      - code2llm\n      - refactor\n      - llm-ready\n"
    assert expected in (updated or "")


def test_add_label_to_ticket_yaml_text_appends_block_label_before_next_field() -> None:
    text = """sprint:
  tickets:
    STARTER-268:
      labels:
      - code2llm
      name: Refactor helper
    STARTER-269:
      name: Next
"""

    updated = _add_label_to_ticket_yaml_text(text, "STARTER-268", "llm-ready")

    assert updated is not None
    assert "      labels:\n      - code2llm\n      - llm-ready\n      name:" in updated
