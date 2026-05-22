"""``koru wizard`` — interactive bootstrap for new koru users.

Detects available IDEs (installed + running), helps pick a project,
walks a JSON-driven decision tree, and creates a first planfile ticket
matching the chosen strategy (architecture, frontend, backend, CQRS+ES, …).

The tree lives in :mod:`koru.wizard.strategies` (``strategies.json``) and is
fully user-editable. Optional ``--llx`` invokes the ``llx`` package to expand
branches dynamically based on the analysed project.
"""

from koru.wizard.cli import wizard_main
from koru.wizard.ide import (
    DetectedIDE,
    discover_installed_ides,
    summarize_ides,
)
from koru.wizard.project import ProjectCandidate, propose_projects
from koru.wizard.templates import TemplateInfo, format_templates_list, list_templates
from koru.wizard.tree import (
    StrategyTree,
    TicketTemplate,
    TreeNode,
    TreeOption,
    load_tree,
    walk,
    walk_path,
)

__all__ = [
    "wizard_main",
    "DetectedIDE",
    "discover_installed_ides",
    "summarize_ides",
    "ProjectCandidate",
    "propose_projects",
    "StrategyTree",
    "TreeNode",
    "TreeOption",
    "TicketTemplate",
    "load_tree",
    "walk",
    "walk_path",
    "TemplateInfo",
    "list_templates",
    "format_templates_list",
]
