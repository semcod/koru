"""Scanners for semcod quality artifacts (jscpd, code2llm, testql, redup, vallm, etc.).

Extracted from koru.scan to decompose the god module and isolate external tool
report parsing from core scan collection and execution.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from koru.scan_types import Suggestion


def _scan_jscpd_report(project: Path) -> list[Suggestion]:
    path = project / ".jscpd" / "jscpd-report.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    total = (data.get("statistics") or {}).get("total") or {}
    dup_lines = int(total.get("duplicatedLines") or 0)
    if dup_lines <= 0:
        return []
    pct = float(total.get("percentage") or 0)
    clones = int(total.get("clones") or 0)
    rel = str(path.relative_to(project))
    pr = "high" if pct >= 15.0 or dup_lines >= 50_000 else "normal"
    return [
        Suggestion(
            signal="jscpd_report",
            title="Reduce jscpd duplicate-code hotspots (semcod scan)",
            description=(
                f"`{rel}`: {dup_lines} duplicated lines ({pct:.1f}% of scanned LOC), "
                f"{clones} clone groups. Triage largest clones first; re-run jscpd after refactors."
            ),
            priority=pr,
            labels=("quality", "duplication", "jscpd", "scan"),
            files=(rel,),
        ),
    ]


_TOON_GOD_RE = re.compile(
    r"^\s*🔴\s+GOD\s+(?P<path>\S+)\s*=\s*(?P<loc>\d+)L,\s*(?P<classes>\d+)\s+classes?,\s*(?P<methods>\d+)m",
    re.MULTILINE,
)
_TOON_CC_RE = re.compile(
    r"^\s*🟡\s+CC\s+(?P<func>\S+)\s+CC=(?P<cc>\d+)\s+\(limit:\s*(?P<limit>\d+)\)",
    re.MULTILINE,
)
_TOON_DUP_RE = re.compile(
    r"^\s*🔴\s+DUP\s+(?P<count>\d+)\s+(?:duplicate\s+)?class(?:es)?(?:\s+groups?)?",
    re.MULTILINE,
)
_TOON_REFACTOR_ITEM_RE = re.compile(r"^\s*(?P<num>\d+)\.\s+(?P<desc>.+?)\s*\((?P<note>[^)]+)\)\s*$")
_TOON_LAYER_HOTSPOT_RE = re.compile(
    r"^\s*│\s*!!\s+(?P<module>\S+)\s+(?P<loc>\d+)L\s+"
    r"(?P<classes>\d+)C\s+(?P<methods>\d+)m\s+CC=(?P<cc>[0-9.]+)",
    re.MULTILINE,
)


# code2llm artifact probe locations, most preferred first: the copy under
# ``<project>/project/`` wins over a repo-root copy of the same artifact.
_ANALYSIS_ARTIFACT_PATHS = (
    "project/analysis.toon.yaml",
    "project/analysis.toon",
    "analysis.toon.yaml",
)
_PLANFILE_TICKETS_ARTIFACT_PATHS = (
    "project/planfile-tickets.yaml",
    "planfile-tickets.yaml",
)
_CALLS_ARTIFACT_PATHS = ("project/calls.yaml", "calls.yaml")


def _find_analysis_file(project: Path) -> tuple[Path | None, str]:
    """Find the code2llm analysis file and return (path, relative_path)."""
    found = _first_existing_artifact(project, _ANALYSIS_ARTIFACT_PATHS)
    return found if found is not None else (None, "")


_CC_LOCATION_RE = re.compile(r"at `(?P<file>[^`:]+):(?P<line>\d+)`")


def _load_yaml_mapping(project: Path, rel_paths: tuple[str, ...]) -> dict | None:
    found = _first_existing_artifact(project, rel_paths)
    if found is None:
        return None
    try:
        payload = yaml.safe_load(found[0].read_text(encoding="utf-8", errors="ignore"))
    except (OSError, yaml.YAMLError):
        return None
    return payload if isinstance(payload, dict) else None


def _add_location(locations: dict[str, list[str]], alias: str, located: str) -> None:
    bucket = locations.setdefault(alias, [])
    if located not in bucket:
        bucket.append(located)


def _location_from_cc_ticket(ticket: object) -> tuple[str, str] | None:
    if not isinstance(ticket, dict) or ticket.get("signal") != "code2llm_cc":
        return None
    files = [str(f) for f in (ticket.get("files") or []) if f]
    if not files:
        return None
    match = _CC_LOCATION_RE.search(str(ticket.get("description") or ""))
    located = f"{files[0]}:{match.group('line')}" if match else files[0]
    key = str(ticket.get("dedupe_key") or "").rsplit(":", 1)[-1].strip()
    if not key:
        return None
    return key, located


def _code2llm_cc_locations(project: Path) -> dict[str, list[str]]:
    """Map a function name to the source file(s) that define it."""
    payload = _load_yaml_mapping(project, _PLANFILE_TICKETS_ARTIFACT_PATHS)
    if payload is None:
        return {}

    locations: dict[str, list[str]] = {}
    for ticket in payload.get("tickets") or []:
        result = _location_from_cc_ticket(ticket)
        if result is None:
            continue
        key, located = result
        for alias in {key, key.rsplit(".", 1)[-1]}:
            _add_location(locations, alias, located)

    _merge_call_graph_locations(project, locations)
    return locations


_MODULE_SUFFIXES = (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".php")


def _resolve_module_path(project: Path, module: str) -> str | None:
    stem = project / Path(*module.split("."))
    match = next(
        (stem.with_suffix(sfx) for sfx in _MODULE_SUFFIXES if stem.with_suffix(sfx).is_file()),
        None,
    )
    return str(match.relative_to(project)) if match else None


def _code2llm_module_paths(project: Path) -> dict[str, str]:
    """Map short module names from LAYERS rows to concrete source files."""
    payload = _load_yaml_mapping(project, _CALLS_ARTIFACT_PATHS)
    if payload is None:
        return {}

    nodes = payload.get("nodes")
    if not isinstance(nodes, dict):
        return {}

    resolved_modules: dict[str, str | None] = {}
    out: dict[str, str] = {}
    for node in nodes.values():
        if not isinstance(node, dict):
            continue
        module = str(node.get("module") or "").strip()
        if not module:
            continue
        if module not in resolved_modules:
            resolved_modules[module] = _resolve_module_path(project, module)
        rel_path = resolved_modules[module]
        if not rel_path:
            continue
        short = module.rsplit(".", 1)[-1]
        out.setdefault(short, rel_path)
        stem = Path(rel_path).stem
        out.setdefault(stem, rel_path)
    return out


def _merge_call_graph_locations(project: Path, locations: dict[str, list[str]]) -> None:
    """Fill location gaps from the code2llm call graph."""
    payload = _load_yaml_mapping(project, _CALLS_ARTIFACT_PATHS)
    nodes = payload.get("nodes") if payload else None
    if not isinstance(nodes, dict):
        return

    resolved: dict[str, str | None] = {}
    for qualified, node in nodes.items():
        if not isinstance(node, dict):
            continue
        name = str(node.get("name") or "").strip()
        module = str(node.get("module") or "").strip()
        if not name or not module:
            continue
        if module not in resolved:
            resolved[module] = _resolve_module_path(project, module)
        rel_path = resolved[module]
        if not rel_path:
            continue
        line = node.get("line")
        located = f"{rel_path}:{line}" if isinstance(line, int) else rel_path
        for alias in {str(qualified), name}:
            _add_location(locations, alias, located)


def _file_evidence(project: Path, path: Path, rel: str | None = None) -> dict[str, object]:
    try:
        stat = path.stat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return {}
    return {
        "path": rel or str(path.relative_to(project)),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": digest,
    }


def _code2llm_regenerate_command(project: Path) -> str:
    return (
        f"code2llm {project} -f all -o {project / 'project'} --no-chunk "
        "--exclude '*.md' --planfile-apply --planfile-source koru-project-discovery "
        f"--planfile-sprint current --planfile-project {project} --planfile-limit 20"
    )


def _code2llm_source_context(project: Path, analysis_path: Path, rel: str) -> dict[str, object]:
    return {
        "evidence": {
            "schema": "koru.ticket_evidence.v1",
            "kind": "code2llm_analysis",
            "artifact": _file_evidence(project, analysis_path, rel),
            "regenerate_command": _code2llm_regenerate_command(project),
            "staleness_check": (
                "Regenerate the artifact and compare artifact.sha256 before assuming "
                "this ticket still reflects the current code."
            ),
        }
    }


def _with_source_context(suggestion: Suggestion, context: dict[str, object] | None) -> Suggestion:
    if not context:
        return suggestion
    merged = dict(suggestion.source_context)
    merged.update(context)
    return Suggestion(
        signal=suggestion.signal,
        title=suggestion.title,
        description=suggestion.description,
        priority=suggestion.priority,
        labels=suggestion.labels,
        files=suggestion.files,
        source_context=merged,
    )


def _norm_repo_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _is_extern_vendored_path(path: str) -> bool:
    """True for paths under an ``extern/`` vendored tree."""
    norm = _norm_repo_path(path).lower()
    return norm == "extern" or norm.startswith("extern/")


def _is_extern_mirror_file_group(files: Sequence[str]) -> bool:
    """True when a dup group is only an ``extern/`` ↔ host (e.g. packages/) twin."""
    if len(files) < 2:
        return False
    normalized = [_norm_repo_path(f) for f in files]
    extern = [p for p in normalized if _is_extern_vendored_path(p)]
    other = [p for p in normalized if not _is_extern_vendored_path(p)]
    if not extern or not other:
        return False
    for host in other:
        host_l = host.lower()
        if not any(e.lower().endswith("/" + host_l) or e.lower().endswith(host_l) for e in extern):
            return False
    return True


_TOON_LAYER_ROOT_RE = re.compile(r"^  (?P<root>\S+/)\s+")
_TOON_LAYER_DUP_MODULE_RE = re.compile(
    r"^\s*│\s+(?P<module>\S+)\s+\d+L\s+\d+C\s+\d+m\s+CC=.*×DUP\s*$",
)


def _layers_dup_module_roots(text: str) -> dict[str, set[str]]:
    """Collect ``module -> {layer roots}`` for every ×DUP row in LAYERS."""
    current_root: str | None = None
    module_roots: dict[str, set[str]] = {}
    in_layers = False
    for line in text.splitlines():
        if line.startswith("LAYERS"):
            in_layers = True
            continue
        if in_layers and line.startswith(
            ("HEALTH", "REFACTOR", "PIPELINES", "COUPLING", "EXTERNAL", "HUB", "SMELL"),
        ):
            break
        if not in_layers:
            continue
        if "│" not in line:
            root_m = _TOON_LAYER_ROOT_RE.match(line)
            if root_m:
                current_root = root_m.group("root")
            continue
        mod_m = _TOON_LAYER_DUP_MODULE_RE.match(line)
        if mod_m and current_root:
            module_roots.setdefault(mod_m.group("module"), set()).add(current_root)
    return module_roots


def _layers_dup_modules_are_extern_mirrors(text: str) -> bool | None:
    """Inspect LAYERS ``×DUP`` rows."""
    module_roots = _layers_dup_module_roots(text)
    if not module_roots:
        return None
    for roots in module_roots.values():
        has_extern = any(_is_extern_vendored_path(r) for r in roots)
        has_other = any(not _is_extern_vendored_path(r) for r in roots)
        if not (has_extern and has_other):
            return False
    return True


def _planfile_dup_groups_are_extern_mirrors(project: Path) -> bool | None:
    """Return whether every ``code2llm_dup`` planfile ticket is an extern mirror."""
    payload = _load_yaml_mapping(project, _PLANFILE_TICKETS_ARTIFACT_PATHS)
    if payload is None:
        return None
    groups: list[tuple[str, ...]] = []
    for ticket in payload.get("tickets") or []:
        if not isinstance(ticket, dict) or ticket.get("signal") != "code2llm_dup":
            continue
        files = tuple(str(f) for f in (ticket.get("files") or []) if f)
        if files:
            groups.append(files)
    if not groups:
        return None
    return all(_is_extern_mirror_file_group(files) for files in groups)


def _files_byte_identical(project: Path, files: Sequence[str]) -> bool:
    """True when all existing files share one digest; missing files do not force drift."""
    digests: set[str] = set()
    seen = 0
    for rel in files:
        path = project / rel
        try:
            digests.add(hashlib.sha256(path.read_bytes()).hexdigest())
            seen += 1
        except OSError:
            continue
    if seen == 0:
        return True
    return len(digests) == 1


def _should_skip_code2llm_dup_ticket(
    text: str,
    *,
    project: Path | None = None,
) -> bool:
    """Skip aggregate DUP tickets that only reflect intentional ``extern/`` mirrors."""
    if project is not None:
        plan = _planfile_dup_groups_are_extern_mirrors(project)
        if plan is True:
            payload = _load_yaml_mapping(project, _PLANFILE_TICKETS_ARTIFACT_PATHS)
            for ticket in (payload or {}).get("tickets") or []:
                if not isinstance(ticket, dict) or ticket.get("signal") != "code2llm_dup":
                    continue
                files = [str(f) for f in (ticket.get("files") or []) if f]
                if files and not _files_byte_identical(project, files):
                    return False
            return True
        if plan is False:
            return False
    layers = _layers_dup_modules_are_extern_mirrors(text)
    return layers is True


def _is_rm_duplicates_refactor(desc: str, note: str) -> bool:
    blob = f"{desc} {note}".lower()
    return "duplicate" in blob or "dup group" in blob or "dup groups" in blob


def _parse_dup_suggestions(
    text: str,
    rel: str,
    *,
    source_context: dict[str, object] | None = None,
    project: Path | None = None,
) -> list[Suggestion]:
    """Parse duplication suggestions from analysis text."""
    suggestions: list[Suggestion] = []
    dup_match = _TOON_DUP_RE.search(text)
    if dup_match:
        if _should_skip_code2llm_dup_ticket(text, project=project):
            return []
        count = int(dup_match.group("count"))
        suggestions.append(
            _with_source_context(
                Suggestion(
                    signal="code2llm_dup",
                    title=f"Remove {count} duplicate class groups (code2llm analysis)",
                    description=(
                        f"`{rel}` reports **{count}** duplicate class name groups "
                        "(merged, not pairwise). "
                        "Extract shared helpers/modules; "
                        "re-run the source.context.evidence.regenerate_command to refresh."
                    ),
                    priority="high",
                    labels=("code2llm", "duplication", "refactor", "scan"),
                    files=(rel,),
                ),
                source_context,
            ),
        )
    return suggestions


def _parse_god_module_suggestions(
    text: str,
    rel: str,
    *,
    source_context: dict[str, object] | None = None,
) -> list[Suggestion]:
    """Parse god module suggestions from analysis text."""
    suggestions: list[Suggestion] = []
    for m in _TOON_GOD_RE.finditer(text):
        file_path = m.group("path").strip()
        loc = m.group("loc")
        classes = m.group("classes")
        methods = m.group("methods")
        suggestions.append(
            _with_source_context(
                Suggestion(
                    signal="code2llm_god",
                    title=f"Split god module: {file_path}",
                    description=(
                        f"`{rel}` flags `{file_path}` as a god module "
                        f"({loc} lines, {classes} classes, {methods} methods). "
                        "Split into focused submodules by responsibility."
                    ),
                    priority="high",
                    labels=("code2llm", "god-module", "refactor", "scan"),
                    files=(file_path, rel),
                ),
                source_context,
            ),
        )
    return suggestions


_CC_NOISE_SYMBOLS = frozenset(
    {
        "__dirname",
        "__filename",
        "describe",
        "it",
        "test",
        "beforeEach",
        "afterEach",
        "beforeAll",
        "afterAll",
    }
)
_CC_CONSTANT_NAME_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")


def _is_noise_cc_symbol(func: str) -> bool:
    """Skip CC suggestions that are constants or runtime/test scaffolding."""
    name = func.strip()
    if not name:
        return True
    bare = name.rsplit(".", 1)[-1]
    if bare in _CC_NOISE_SYMBOLS or name in _CC_NOISE_SYMBOLS:
        return True
    return bool(_CC_CONSTANT_NAME_RE.fullmatch(bare))


def _parse_high_cc_suggestions(
    text: str,
    rel: str,
    *,
    source_context: dict[str, object] | None = None,
    locations: dict[str, list[str]] | None = None,
) -> list[Suggestion]:
    """Parse high-CC method suggestions from analysis text."""
    suggestions: list[Suggestion] = []
    cc_seen: set[str] = set()
    for m in _TOON_CC_RE.finditer(text):
        func = m.group("func").strip()
        cc = int(m.group("cc"))
        limit = int(m.group("limit"))
        if func in cc_seen:
            continue
        cc_seen.add(func)
        if _is_noise_cc_symbol(func):
            continue

        found = (locations or {}).get(func) or []
        files = tuple(entry.split(":", 1)[0] for entry in found) or (rel,)
        if len(found) == 1:
            where = f"`{found[0]}`"
        elif found:
            where = "one of " + ", ".join(f"`{entry}`" for entry in found)
        else:
            where = f"a location not recorded in `{rel}`"
        suggestions.append(
            _with_source_context(
                Suggestion(
                    signal="code2llm_cc",
                    title=f"Reduce cyclomatic complexity: {func} (CC={cc}, limit={limit})",
                    description=(
                        f"`{rel}` reports `{func}` with CC={cc} (limit={limit}), "
                        f"defined in {where}. "
                        "Extract sub-functions, simplify conditionals, or split into strategy pattern. "
                        "Preserve behaviour — this is a pure refactor."
                    ),
                    priority="normal",
                    labels=("code2llm", "complexity", "refactor", "scan"),
                    files=files,
                ),
                source_context,
            ),
        )
    return suggestions


def _parse_refactor_suggestions(
    text: str,
    rel: str,
    *,
    source_context: dict[str, object] | None = None,
    skip_duplicate_items: bool = False,
) -> list[Suggestion]:
    """Parse refactor item suggestions from analysis text."""
    suggestions: list[Suggestion] = []
    in_refactor = False
    for line in text.splitlines():
        if line.startswith("REFACTOR"):
            in_refactor = True
            continue
        if in_refactor and line.startswith(("HEALTH", "PIPELINES", "LAYERS")):
            break
        if not in_refactor:
            continue
        rm = _TOON_REFACTOR_ITEM_RE.match(line)
        if not rm:
            continue
        desc = rm.group("desc").strip()
        note = rm.group("note").strip()
        if skip_duplicate_items and _is_rm_duplicates_refactor(desc, note):
            continue
        suggestions.append(
            _with_source_context(
                Suggestion(
                    signal="code2llm_refactor",
                    title=f"code2llm refactor: {desc}",
                    description=(
                        f"REFACTOR item from `{rel}`: **{desc}** ({note}). "
                        "Execute this refactor step; re-run the source.context.evidence.regenerate_command to verify."
                    ),
                    priority="normal",
                    labels=("code2llm", "refactor", "scan"),
                    files=(rel,),
                ),
                source_context,
            ),
        )
    return suggestions


_LAYER_NON_CODE_SUFFIXES = (
    ".md",
    ".markdown",
    ".rst",
    ".txt",
    ".adoc",
    ".html",
    ".htm",
)


def _is_non_code_layer_module(
    module: str,
    *,
    classes: int,
    methods: int,
    cc: float,
) -> bool:
    """Skip docs/data LAYERS rows that are not split-worthy code modules."""
    name = module.strip().lower()
    if any(name.endswith(suffix) for suffix in _LAYER_NON_CODE_SUFFIXES):
        return True
    return classes == 0 and methods == 0 and cc <= 0


def _parse_layer_hotspot_suggestions(
    text: str,
    rel: str,
    *,
    source_context: dict[str, object] | None = None,
    project: Path | None = None,
    module_paths: dict[str, str] | None = None,
) -> list[Suggestion]:
    """Parse large ``LAYERS`` module rows from newer code2llm output."""
    suggestions: list[Suggestion] = []
    seen: set[str] = set()
    for m in _TOON_LAYER_HOTSPOT_RE.finditer(text):
        module = m.group("module").strip()
        if module in seen:
            continue
        seen.add(module)
        loc = int(m.group("loc"))
        classes = int(m.group("classes"))
        methods = int(m.group("methods"))
        cc = float(m.group("cc"))
        if _is_non_code_layer_module(module, classes=classes, methods=methods, cc=cc):
            continue
        if loc < 500 and cc < 12:
            continue
        priority = "high" if loc >= 800 or cc >= 14 else "normal"
        src_path = (module_paths or {}).get(module)
        if src_path is None and project is not None:
            src_path = _resolve_module_path(project, module)
        ticket_files = tuple(dict.fromkeys(p for p in (src_path, rel) if p))
        suggestions.append(
            _with_source_context(
                Suggestion(
                    signal="code2llm_layer_hotspot",
                    title=f"Split large module: {module}",
                    description=(
                        f"`{rel}` flags `{module}` in LAYERS as a large/hot module "
                        f"({loc} lines, {classes} classes, {methods} methods, CC={cc:g}). "
                        "Extract cohesive submodules around stable responsibilities and add "
                        "focused regression tests before broad edits."
                    ),
                    priority=priority,
                    labels=("code2llm", "architecture", "large-module", "refactor", "scan"),
                    files=ticket_files or (rel,),
                ),
                source_context,
            ),
        )
        if len(suggestions) >= 5:
            break
    return suggestions


def _scan_code2llm_analysis(project: Path) -> list[Suggestion]:
    path, rel = _find_analysis_file(project)
    if path is None:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    source_context = _code2llm_source_context(project, path, rel)
    skip_mirror_dups = _should_skip_code2llm_dup_ticket(text, project=project)
    suggestions: list[Suggestion] = []
    suggestions.extend(
        _parse_dup_suggestions(
            text,
            rel,
            source_context=source_context,
            project=project,
        ),
    )
    suggestions.extend(_parse_god_module_suggestions(text, rel, source_context=source_context))
    suggestions.extend(
        _parse_high_cc_suggestions(
            text,
            rel,
            source_context=source_context,
            locations=_code2llm_cc_locations(project),
        ),
    )
    suggestions.extend(
        _parse_refactor_suggestions(
            text,
            rel,
            source_context=source_context,
            skip_duplicate_items=skip_mirror_dups,
        ),
    )
    suggestions.extend(
        _parse_layer_hotspot_suggestions(
            text,
            rel,
            source_context=source_context,
            project=project,
            module_paths=_code2llm_module_paths(project),
        ),
    )
    return suggestions


def _scan_testql_export(project: Path) -> list[Suggestion]:
    path = project / "testql_api_results.json"
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    failed_scenarios = len(re.findall(r"(?m)^❌\s+\S+\.(?:yaml|yml)", text))
    if failed_scenarios < 3:
        return []
    rel = str(path.relative_to(project))
    pr = "high" if failed_scenarios >= 15 else "normal"
    return [
        Suggestion(
            signal="testql_export",
            title="Repair failing TestQL API scenarios (exported log)",
            description=(
                f"`{rel}` shows ~{failed_scenarios} failing scenario(s). "
                "Fix backend routes or refresh generated scenarios; re-export after green runs."
            ),
            priority=pr,
            labels=("testql", "regression", "api", "scan"),
            files=(rel,),
        ),
    ]


def _scan_redup_filtered(project: Path) -> list[Suggestion]:
    path = project / ".redup" / "check.filtered.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    groups = data if isinstance(data, list) else data.get("groups") or data.get("clusters")
    if not isinstance(groups, list) or len(groups) < 20:
        return []
    rel = str(path.relative_to(project))
    return [
        Suggestion(
            signal="redup_filtered",
            title="Drive down redup duplicate groups (filtered JSON)",
            description=(
                f"`{rel}` lists {len(groups)} duplicate groups over the hygiene threshold. "
                "Extract shared helpers / modules; re-run `task quality:redup:report`."
            ),
            priority="normal",
            labels=("redup", "duplication", "python", "scan"),
            files=(rel,),
        ),
    ]


def _scan_redup_changed(project: Path) -> list[Suggestion]:
    path = project / ".redup" / "wup-changed.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    groups = data if isinstance(data, list) else data.get("groups") or data.get("clusters")
    if not isinstance(groups, list) or not groups:
        return []
    rel = str(path.relative_to(project))
    return [
        Suggestion(
            signal="redup_changed",
            title="Review duplicate groups touching recent changes",
            description=(
                f"`{rel}` lists {len(groups)} duplicate group(s) from the WUP/on-change "
                "redup scan. Triage these before running a full duplicate budget gate."
            ),
            priority="normal",
            labels=("redup", "duplication", "wup", "scan"),
            files=(rel,),
        ),
    ]


def _first_existing_artifact(project: Path, candidates: Sequence[str]) -> tuple[Path, str] | None:
    for candidate in candidates:
        path = project / candidate
        if path.is_file():
            return path, candidate
    return None


def _load_structured_artifact(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    if path.suffix.lower() == ".json":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None


def _intish(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"failed", "fail", "error", "errors", "red", "critical"}:
            return 1
        try:
            return int(float(text))
        except ValueError:
            return 0
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len(value)
    return 0


def _sum_structured_counts(data: object, keys: frozenset[str]) -> int:
    """Best-effort issue counter for small semcod JSON/YAML reports."""
    if isinstance(data, dict):
        total = 0
        for key, value in data.items():
            key_text = str(key).lower().replace("-", "_")
            if key_text in keys:
                total += _intish(value)
            elif key_text == "status" and str(value).strip().lower() in {
                "failed",
                "failure",
                "error",
                "red",
            }:
                total += 1
            else:
                total += _sum_structured_counts(value, keys)
        return total
    if isinstance(data, list):
        return sum(_sum_structured_counts(item, keys) for item in data)
    return 0


def _scan_vallm_validation(project: Path) -> list[Suggestion]:
    found = _first_existing_artifact(
        project,
        (
            "validation.toon.yaml",
            "project/validation.toon.yaml",
            "vallm-validation.toon.yaml",
            "vallm-report.yaml",
            ".vallm/report.yaml",
        ),
    )
    if found is None:
        return []
    path, rel = found
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    errors = 0
    warnings = 0
    err_match = re.search(r"(?m)^\s*ERRORS\[(?P<count>\d+)\]", text)
    warn_match = re.search(r"(?m)^\s*WARNINGS\[(?P<count>\d+)\]", text)
    if err_match:
        errors = int(err_match.group("count"))
    if warn_match:
        warnings = int(warn_match.group("count"))
    if errors <= 0 and warnings < 10:
        return []
    priority = "high" if errors > 0 else "normal"
    return [
        Suggestion(
            signal="vallm_validation",
            title="Repair VALLM validation findings",
            description=(
                f"`{rel}` reports {errors} error(s) and {warnings} warning(s). "
                "Fix the highest-impact validation failures first, then re-run "
                "`vallm validate` / the project validation task and refresh the report."
            ),
            priority=priority,
            labels=("vallm", "validation", "scan"),
            files=(rel,),
        ),
    ]


def _scan_structured_semcod_report(
    project: Path,
    *,
    candidates: Sequence[str],
    signal: str,
    title: str,
    command_hint: str,
    labels: tuple[str, ...],
    keys: frozenset[str],
    high_threshold: int = 10,
) -> list[Suggestion]:
    found = _first_existing_artifact(project, candidates)
    if found is None:
        return []
    path, rel = found
    data = _load_structured_artifact(path)
    if data is None:
        return []
    count = _sum_structured_counts(data, keys)
    if count <= 0:
        return []
    priority = "high" if count >= high_threshold else "normal"
    return [
        Suggestion(
            signal=signal,
            title=title,
            description=(
                f"`{rel}` reports {count} actionable finding(s). "
                f"Triage and repair the report findings, then re-run `{command_hint}` "
                "and refresh the artifact before closing the ticket."
            ),
            priority=priority,
            labels=labels,
            files=(rel,),
        ),
    ]


def _scan_pyqual_report(project: Path) -> list[Suggestion]:
    return _scan_structured_semcod_report(
        project,
        candidates=(
            ".pyqual/report.json",
            ".pyqual/report.yaml",
            "pyqual-report.json",
            "pyqual-report.yaml",
            "quality-report.yaml",
        ),
        signal="pyqual_report",
        title="Repair PyQual quality findings",
        command_hint="pyqual check",
        labels=("pyqual", "quality", "scan"),
        keys=frozenset(
            {
                "failed",
                "failures",
                "failed_checks",
                "errors",
                "issues",
                "violations",
                "findings",
            },
        ),
    )


def _scan_prefact_report(project: Path) -> list[Suggestion]:
    return _scan_structured_semcod_report(
        project,
        candidates=(
            ".prefact/report.json",
            ".prefact/results.json",
            "prefact-report.json",
            "prefact-results.json",
        ),
        signal="prefact_report",
        title="Resolve Prefact pre-refactor findings",
        command_hint="prefact check",
        labels=("prefact", "refactor", "quality", "scan"),
        keys=frozenset(
            {
                "failed",
                "failures",
                "errors",
                "issues",
                "findings",
                "violations",
                "blocking",
            },
        ),
    )


def _scan_regix_report(project: Path) -> list[Suggestion]:
    return _scan_structured_semcod_report(
        project,
        candidates=(
            ".regix/report.json",
            ".regix/gates.json",
            "regix-report.json",
            "regix-gates.json",
        ),
        signal="regix_report",
        title="Repair Regix regression gate findings",
        command_hint="regix gates",
        labels=("regix", "regression", "scan"),
        keys=frozenset(
            {
                "failed",
                "failures",
                "failed_gates",
                "regressions",
                "errors",
                "violations",
            },
        ),
    )


def _scan_redsl_report(project: Path) -> list[Suggestion]:
    return _scan_structured_semcod_report(
        project,
        candidates=(
            ".redsl/report.json",
            ".redsl/gate.json",
            "redsl-report.json",
            "redsl-report.yaml",
            "redsl-gate.json",
        ),
        signal="redsl_report",
        title="Repair RedSL gate findings",
        command_hint="redsl gate check .",
        labels=("redsl", "gate", "scan"),
        keys=frozenset(
            {
                "failed",
                "failures",
                "errors",
                "issues",
                "findings",
                "violations",
                "regressions",
            },
        ),
    )


_METRUN_BOTTLENECKS_RE = re.compile(r"(?m)^BOTTLENECKS\[(?P<count>\d+)\]")
_METRUN_TOP_SCORE_RE = re.compile(r"(?m)^\s*top_score:\s*(?P<score>[0-9.]+)")
_METRUN_TOP_NAME_RE = re.compile(r"(?m)^\s*top_name:\s*(?P<name>\S+)")


_PFIX_FAIL_STATUSES = frozenset({"critical", "error", "fail", "failed", "failure"})


def _count_pfix_diagnose_issues(data: object) -> tuple[int, tuple[str, ...]]:
    if not isinstance(data, list):
        return 0, ()
    count = 0
    files: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").strip().lower()
        if status not in _PFIX_FAIL_STATUSES:
            continue
        count += 1
        path = str(item.get("abs_path") or item.get("file") or "").strip()
        if path:
            files.append(path.replace("\\", "/"))
    return count, tuple(dict.fromkeys(files))


def _scan_pfix_report(project: Path) -> list[Suggestion]:
    found = _first_existing_artifact(
        project,
        (
            ".pfix/diagnose.json",
            "pfix-diagnose.json",
            "diag_report.json",
        ),
    )
    if found is None:
        return []
    path, rel = found
    data = _load_structured_artifact(path)
    if data is None:
        return []
    count, files = _count_pfix_diagnose_issues(data)
    if count <= 0:
        count = _sum_structured_counts(
            data,
            frozenset(
                {
                    "failed",
                    "failures",
                    "errors",
                    "issues",
                    "findings",
                    "violations",
                    "critical",
                },
            ),
        )
    if count <= 0:
        return []
    priority = "high" if count >= 3 else "normal"
    file_hint = f" Affected paths: {', '.join(files[:5])}." if files else ""
    return [
        Suggestion(
            signal="pfix_diagnose",
            title="Resolve Pfix environment diagnostic findings",
            description=(
                f"`{rel}` reports {count} critical/error diagnostic(s). "
                f"Run `pfix diagnose --json --output {rel}` (or fix manually), "
                "then refresh the report before closing the ticket."
                f"{file_hint}"
            ),
            priority=priority,
            labels=("pfix", "diagnostics", "scan"),
            files=((rel, *files[:8]) if files else (rel,)),
        ),
    ]


def _scan_metrun_report(project: Path) -> list[Suggestion]:
    found = _first_existing_artifact(
        project,
        (
            "project/metrun.toon.yaml",
            "metrun.toon.yaml",
            ".metrun/metrun.toon.yaml",
        ),
    )
    if found is None:
        return []
    path, rel = found
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    count_match = _METRUN_BOTTLENECKS_RE.search(text)
    bottlenecks = int(count_match.group("count")) if count_match else 0
    if bottlenecks <= 0:
        return []
    score_match = _METRUN_TOP_SCORE_RE.search(text)
    top_score = float(score_match.group("score")) if score_match else 0.0
    name_match = _METRUN_TOP_NAME_RE.search(text)
    top_name = name_match.group("name") if name_match else "hotspot"
    priority = "high" if bottlenecks >= 3 or top_score >= 8.0 else "normal"
    return [
        Suggestion(
            signal="metrun_report",
            title=f"Address Metrun performance bottleneck: {top_name}",
            description=(
                f"`{rel}` reports {bottlenecks} bottleneck(s) "
                f"(top `{top_name}`, score={top_score:.2f}). "
                "Review the critical path and suggestions in the report, "
                "then re-run `metrun scan <script>` or `metrun profile` "
                "and refresh the artifact before closing the ticket."
            ),
            priority=priority,
            labels=("metrun", "performance", "scan"),
            files=(rel,),
        ),
    ]


def _todo2code_plan_suggestion(
    plan: dict[str, Any],
    *,
    project: Path,
    plans_rel: str,
    is_useful_plan: Callable[..., bool],
    plan_useful_paths: Callable[..., list[str]],
    priority_map: Mapping[str, str],
    source: str,
    dedupe_key: Callable[[dict[str, Any]], str],
) -> Suggestion | None:
    """Convert one useful grounded plan into a scan suggestion."""
    if not is_useful_plan(plan, project=project):
        return None
    paths = plan_useful_paths(plan, project=project)
    if not paths:
        return None
    title_raw = str(plan.get("title") or "todo2code code-change plan").strip()
    title = title_raw if len(title_raw) <= 140 else title_raw[:139].rstrip() + "…"
    description = str(plan.get("description") or title_raw).strip()
    priority = priority_map.get(str(plan.get("priority") or "").upper(), "normal")
    if priority not in {"high", "normal", "low"}:
        priority = "normal"
    return Suggestion(
        signal="todo2code_plan",
        title=f"[todo2code] {title}",
        description=(
            f"{description}\n\nSource: `{plans_rel}` "
            f"(plan id {plan.get('id') or 'n/a'}). Implement only declared target paths."
        ),
        priority=priority,
        labels=("todo2code", "code-change", "scan", "useful-code-change"),
        files=tuple(paths[:12]),
        source_context=_todo2code_source_context(plan, dedupe_key=dedupe_key, source=source),
    )


def _todo2code_source_context(
    plan: dict[str, Any],
    *,
    dedupe_key: Callable[[dict[str, Any]], str],
    source: str,
) -> dict[str, Any]:
    evidence = plan.get("evidence") if isinstance(plan.get("evidence"), dict) else {}
    return {
        "signal": "todo2code_code_change_plan",
        "dedupe_key": dedupe_key(plan),
        "plan_id": str(plan.get("id") or "").strip() or None,
        "plan_hash": str(plan.get("planHash") or "").strip() or None,
        "source_tool": source,
        "diagnostic_ids": [str(v) for v in (evidence.get("diagnosticIds") or []) if str(v).strip()],
    }


def _scan_todo2code_plans(project: Path) -> list[Suggestion]:
    """Useful grounded code-change plans from ``t2c`` artifacts."""
    try:
        from koru.autonomy.code_change_usefulness import is_useful_plan, plan_useful_paths
        from koru.autonomy.todo2code_discovery import (
            _PRIORITY_MAP,
            _plan_dedupe_key,
            find_latest_plans_path,
        )
        from koru.autonomy.todo2code_discovery import (
            DEFAULT_SOURCE as TODO2CODE_SOURCE,
        )
    except Exception:  # noqa: BLE001
        return []

    plans_path = find_latest_plans_path(project / ".intent")
    if plans_path is None:
        return []
    try:
        data = json.loads(plans_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    plans = [p for p in (data.get("plans") or []) if isinstance(p, dict)]
    try:
        plans_rel = str(plans_path.relative_to(project))
    except ValueError:
        plans_rel = str(plans_path)

    suggestions: list[Suggestion] = []
    for plan in plans:
        suggestion = _todo2code_plan_suggestion(
            plan,
            project=project,
            plans_rel=plans_rel,
            is_useful_plan=is_useful_plan,
            plan_useful_paths=plan_useful_paths,
            priority_map=_PRIORITY_MAP,
            source=TODO2CODE_SOURCE,
            dedupe_key=_plan_dedupe_key,
        )
        if suggestion is not None:
            suggestions.append(suggestion)
    return suggestions


def scan_semcod_quality_artifacts(project: Path) -> list[Suggestion]:
    """Quality tickets from semcod-adjacent tool exports."""
    project = project.resolve()
    out: list[Suggestion] = []
    out.extend(_scan_jscpd_report(project))
    out.extend(_scan_code2llm_analysis(project))
    out.extend(_scan_testql_export(project))
    out.extend(_scan_redup_filtered(project))
    out.extend(_scan_redup_changed(project))
    out.extend(_scan_vallm_validation(project))
    out.extend(_scan_pyqual_report(project))
    out.extend(_scan_prefact_report(project))
    out.extend(_scan_regix_report(project))
    out.extend(_scan_redsl_report(project))
    out.extend(_scan_metrun_report(project))
    out.extend(_scan_pfix_report(project))
    out.extend(_scan_todo2code_plans(project))
    return out


__all__ = [
    "_ANALYSIS_ARTIFACT_PATHS",
    "_CALLS_ARTIFACT_PATHS",
    "_PLANFILE_TICKETS_ARTIFACT_PATHS",
    "_code2llm_cc_locations",
    "_code2llm_module_paths",
    "_find_analysis_file",
    "_first_existing_artifact",
    "_load_yaml_mapping",
    "_scan_code2llm_analysis",
    "_scan_jscpd_report",
    "_scan_metrun_report",
    "_scan_pfix_report",
    "_scan_prefact_report",
    "_scan_pyqual_report",
    "_scan_redsl_report",
    "_scan_redup_changed",
    "_scan_redup_filtered",
    "_scan_regix_report",
    "_scan_structured_semcod_report",
    "_scan_testql_export",
    "_scan_todo2code_plans",
    "_scan_vallm_validation",
    "_should_skip_code2llm_dup_ticket",
    "scan_semcod_quality_artifacts",
]
