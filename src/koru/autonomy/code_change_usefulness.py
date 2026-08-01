"""Shared usefulness rules for code-change plans and planfile tickets.

Filters out vendored trees, binary assets, generated analysis dumps, and
wildcard paths so idle discovery does not flood the queue with non-actionable
work. Mirrors the hardened ``isPlannablePath`` policy in todo2code.
"""

from __future__ import annotations

import json
import re
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

NON_SOURCE_DIR_SEGMENTS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        ".testvenv",
        "testvenv",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".code2llm_cache",
        "__pycache__",
        "node_modules",
        "site-packages",
        "dist-packages",
        "dist",
        "build",
        "coverage",
        "htmlcov",
        ".eggs",
        "eggs",
        "vendor",
        "third_party",
        "third-party",
        ".intent",
        ".intent-koru-verify",
        ".intent-t2c-semcod-batch",
        ".intent-t2c-test",
    }
)

NON_SOURCE_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".svg",
        ".pdf",
        ".mp4",
        ".webm",
        ".zip",
        ".tar",
        ".gz",
        ".tgz",
        ".whl",
        ".egg",
        ".so",
        ".dylib",
        ".dll",
        ".pyc",
        ".pyo",
        ".class",
        ".o",
        ".a",
        ".lock",
        ".map",
    }
)

GENERATED_ANALYSIS_BASENAMES = frozenset(
    {
        "analysis.toon",
        "analysis.toon.yaml",
        "analysis.yaml",
        "map.toon",
        "map.toon.yaml",
        "flow.toon",
        "flow.toon.yaml",
        "flow.mmd",
        "flow.png",
        "calls.mmd",
        "calls.png",
        "calls.toon",
        "calls.toon.yaml",
        "calls.yaml",
        "compact_flow.mmd",
        "compact_flow.png",
        "duplication.toon",
        "duplication.toon.yaml",
        "evolution.toon",
        "evolution.toon.yaml",
        "validation.toon",
        "validation.toon.yaml",
        "context.md",
        "dashboard.html",
        "index.html",
        "prompt.txt",
        "analysis.json",
        ".code2llm_incremental.json",
        "code2llm_incremental.json",
    }
)

SOURCE_EXTENSIONS = frozenset(
    {
        ".py",
        ".pyi",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".kts",
        ".cs",
        ".cpp",
        ".cc",
        ".c",
        ".h",
        ".hpp",
        ".rb",
        ".php",
        ".swift",
        ".scala",
        ".sh",
        ".bash",
        ".zsh",
        ".sql",
        ".yaml",
        ".yml",
        ".toml",
        ".json",
        ".md",
        ".rst",
        ".html",
        ".css",
        ".scss",
        ".vue",
        ".svelte",
    }
)

GOVERNANCE_BASENAMES = frozenset(
    {
        "AGENTS.md",
        "POLICY.md",
        "CONTRIBUTING.md",
        "TODO.md",
        "project.sh",
        "project.bat",
    }
)
_GOVERNANCE_BASENAMES_LOWER = frozenset(value.lower() for value in GOVERNANCE_BASENAMES)

_TICKET_DIRECTORY_RE = re.compile(r"^ticket-[0-9]+$", re.IGNORECASE)


def normalize_path(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


def _declared_governance_patterns(project: Path | None) -> tuple[list[str], bool]:
    """Return target-owned governance globs and whether its manifest is invalid."""
    if project is None:
        return [], False
    manifest_path = project / ".governance" / "manifest.json"
    if not manifest_path.is_file():
        return [], False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_patterns = manifest["governancePaths"]
        if not isinstance(raw_patterns, list):
            raise TypeError("governancePaths must be a list")
        patterns = [normalize_path(value) for value in raw_patterns if str(value).strip()]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return [], True
    return patterns, False


def is_governance_owned_path(value: str, *, project: Path | None = None) -> bool:
    """Return whether autonomous source patches must not own *value*.

    Ticket directories contain human/agent intent, decisions, logs and evidence.
    They are inputs to todo2code communication analysis, never implementation
    targets. Root governance documents and bootstrap scripts have the same
    protection: changing the policy that authorizes a patch from inside that
    patch would make the policy circular.
    """
    normalized = normalize_path(value)
    segments = [part for part in normalized.split("/") if part]
    if not segments:
        return False
    patterns, invalid_manifest = _declared_governance_patterns(project)
    if invalid_manifest:
        # A malformed target policy cannot safely authorize any autonomous path.
        return True
    if any(fnmatchcase(normalized, pattern) for pattern in patterns):
        return True
    if segments[0].lower() == ".governance":
        return True
    if segments[-1].lower() in _GOVERNANCE_BASENAMES_LOWER:
        return True
    if segments[0].lower() != "project":
        return False
    if len(segments) == 2 and segments[1].lower() in {"readme.md", "tickets.md"}:
        return True
    return len(segments) >= 2 and bool(_TICKET_DIRECTORY_RE.fullmatch(segments[1]))


def is_useful_code_change_path(value: str, *, project: Path | None = None) -> bool:
    """Return True when a path is a concrete, in-repo implementation target."""
    normalized = normalize_path(value)
    if not normalized or normalized.startswith("/"):
        return False
    # Symbols and line anchors belong in ``target.symbols``. Accepting a value
    # such as ``src/module.py::symbol`` as a path can create a literally named,
    # non-source file instead of modifying the intended module.
    if ":" in normalized or "\n" in normalized or "\r" in normalized or "\0" in normalized:
        return False
    if is_governance_owned_path(normalized, project=project):
        return False
    segments = [part for part in normalized.split("/") if part]
    if not segments or ".." in segments or "*" in segments:
        return False
    if any(ch in normalized for ch in "*?[]{}"):
        return False

    for segment in segments:
        if segment in NON_SOURCE_DIR_SEGMENTS:
            return False
        if segment.endswith(".egg-info") or segment.endswith(".dist-info"):
            return False

    basename = segments[-1]
    if basename in GENERATED_ANALYSIS_BASENAMES:
        return False

    dot = basename.rfind(".")
    if dot > 0:
        ext = basename[dot:].lower()
        if ext in NON_SOURCE_EXTENSIONS:
            return False

    if segments[0] == "project" and (
        basename.endswith(".toon")
        or basename.endswith(".toon.yaml")
        or basename.endswith(".mmd")
        or basename.endswith(".json")
        or basename in {"prompt.txt", "README.md"}
    ):
        return False

    if segments[0] in {".koru", ".code2llm_cache", ".planfile"}:
        return False
    if "code2llm_incremental" in basename:
        return False

    return True


def useful_paths(
    paths: list[str] | tuple[str, ...] | None,
    *,
    project: Path | None = None,
) -> list[str]:
    return [
        path
        for path in (normalize_path(p) for p in (paths or []))
        if is_useful_code_change_path(path, project=project)
    ]


def plan_useful_paths(plan: dict[str, Any], *, project: Path | None = None) -> list[str]:
    target = plan.get("target") if isinstance(plan.get("target"), dict) else {}
    paths = useful_paths(list(target.get("paths") or []), project=project)
    if paths:
        return paths
    changes = plan.get("changes") if isinstance(plan.get("changes"), list) else []
    return useful_paths(
        [
            str(change.get("path") or "")
            for change in changes
            if isinstance(change, dict)
        ],
        project=project,
    )


def plan_usefulness_score(plan: dict[str, Any], *, project: Path | None = None) -> float:
    """Higher score = more worth turning into a planfile ticket."""
    paths = plan_useful_paths(plan, project=project)
    if not paths:
        return -1.0

    score = 10.0
    evidence = plan.get("evidence") if isinstance(plan.get("evidence"), dict) else {}
    diagnostic_ids = [str(v) for v in (evidence.get("diagnosticIds") or []) if str(v).strip()]
    record_ids = [str(v) for v in (evidence.get("recordIds") or []) if str(v).strip()]

    # Prefer TODO-style plans over pure changelog noise.
    if any(rid.startswith("INT-TODO-") for rid in record_ids):
        score += 8.0
    if any(rid.startswith("INT-CHANGELOG-") for rid in record_ids) and not any(
        rid.startswith("INT-TODO-") for rid in record_ids
    ):
        score -= 3.0

    source_hits = 0
    for path in paths:
        ext = Path(path).suffix.lower()
        if ext in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}:
            source_hits += 1
            score += 4.0
        elif ext in SOURCE_EXTENSIONS:
            score += 1.5
        if path.startswith("src/") or path.startswith("lib/") or "/src/" in path:
            score += 3.0
        if path.startswith("tests/") or path.startswith("test/"):
            score += 1.0
        if path.startswith("docs/") or path.endswith(".md"):
            score -= 1.5
        if project is not None and (project / path).is_file():
            score += 0.5

    target = plan.get("target") if isinstance(plan.get("target"), dict) else {}
    symbols = [str(s) for s in (target.get("symbols") or []) if str(s).strip()]
    if symbols:
        score += 2.0 + min(3.0, 0.5 * len(symbols))

    priority = str(plan.get("priority") or "").upper()
    score += {"P0": 5.0, "P1": 3.0, "P2": 1.0, "P3": 0.0}.get(priority, 0.5)

    if diagnostic_ids:
        score += 1.0
    if source_hits == 0 and all(path.endswith(".md") for path in paths):
        score -= 4.0

    return score


def is_useful_plan(plan: dict[str, Any], *, project: Path | None = None, min_score: float = 8.0) -> bool:
    evidence = plan.get("evidence") if isinstance(plan.get("evidence"), dict) else {}
    record_ids = [str(value) for value in (evidence.get("recordIds") or [])]
    # A CHANGELOG-only gap says that historical evidence is incomplete.  It
    # does not authorize a new source edit: the release author/reviewer must
    # either identify the old commit or correct the release note.  Mixing these
    # audit records into the autonomous queue caused models to redo changes
    # already present in the repository.
    if record_ids and all(value.startswith("INT-CHANGELOG-") for value in record_ids):
        return False
    risk = plan.get("risk") if isinstance(plan.get("risk"), dict) else {}
    # Blocking/high-risk findings commonly mean a checked/completed declaration
    # lacks proof.  They require review or decomposition; hydrating them as R1
    # silently widened the authority of the autonomous patch runner.
    if str(risk.get("level") or "").strip().lower() == "high":
        return False
    paths = plan_useful_paths(plan, project=project)
    changes = plan.get("changes") if isinstance(plan.get("changes"), list) else []
    actions = {
        normalize_path(str(change.get("path") or "")): str(change.get("action") or "modify").lower()
        for change in changes
        if isinstance(change, dict)
    }
    if project is not None:
        for path in paths:
            exists = (project / path).is_file()
            action = actions.get(path, "modify")
            if action == "create" and exists:
                return False
            if action != "create" and not exists:
                return False
    return plan_usefulness_score(plan, project=project) >= min_score


__all__ = [
    "GENERATED_ANALYSIS_BASENAMES",
    "NON_SOURCE_DIR_SEGMENTS",
    "NON_SOURCE_EXTENSIONS",
    "SOURCE_EXTENSIONS",
    "GOVERNANCE_BASENAMES",
    "is_governance_owned_path",
    "is_useful_code_change_path",
    "is_useful_plan",
    "normalize_path",
    "plan_useful_paths",
    "plan_usefulness_score",
    "useful_paths",
]
