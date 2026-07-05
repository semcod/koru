"""Domain layer packages (pure logic, no I/O adapters).

Keep this ``__init__`` present: ``[tool.setuptools.packages.find]`` skips
directories without one, and a fresh ``pip install -e .`` (CI) then cannot
import ``koru.domain.*`` even though a long-lived dev venv (compat-mode
editable) still can — CI went red on 2026-07-05 exactly this way.
"""
