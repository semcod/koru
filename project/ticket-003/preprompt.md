# Preprompt — ticket-003

Use Ruff's own safe import-order fixes for the reported I001 findings and
manually wrap only `src/koru/init.py`'s E501 shell-template line. Review the
resulting diff for semantic changes. Run Ruff and focused Koru tests.
