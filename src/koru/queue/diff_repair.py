"""Turn an agent's reply into a diff git will accept.

Models produce unified diffs with reliable defects: fenced in prose, missing
the ``---``/``+++`` headers, hunk ranges off by one. Those are all derivable
from the diff body, so they are repaired here rather than costing a retry.
What is *not* repaired is anything ambiguous — a hunk line with no marker
could be context, an addition or a deletion, and guessing would risk writing
the wrong change into someone's code.

Also supports deterministic synthesis of unified diffs from SEARCH/REPLACE blocks
and fuzzy hunk repair when a project path is provided.
"""

from __future__ import annotations

import difflib
import os
import re
from collections.abc import Iterable
from pathlib import Path

_FENCE_RE = re.compile(
    r"```[a-zA-Z0-9_-]*\s*\n(?P<body>.*?)(?:\n```|\Z)",
    re.DOTALL,
)


_DIFF_START_RE = re.compile(r"^(diff --git |--- (?:a/|/dev/null))", re.MULTILINE)


_HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_len>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_len>\d+))? @@(?P<tail>.*)$",
)


_GIT_HEADER_RE = re.compile(r"^diff --git a/(?P<old>.+?) b/(?P<new>.+?)\s*$")


_SYMLINK_MODE_RE = re.compile(r"^(?:new file mode|new mode) 120000\s*$", re.MULTILINE)


_SEARCH_REPLACE_RE = re.compile(
    r"<{4,9}\s*SEARCH[ \t]*\r?\n(?P<search>.*?)\r?\n={4,9}[ \t]*\r?\n(?P<replace>.*?)\r?\n>{4,9}\s*REPLACE",
    re.DOTALL,
)

_FILE_HEADER_LINE_RE = re.compile(
    r"^(?:#{1,4}\s*(?:(?:NEW\s+)?FILE\s*:\s*)?|FILE\s*:\s*|File\s*:\s*|\*\*File\s*:\*\*\s*)?`?(?P<path>[A-Za-z0-9_./-]+\.[A-Za-z0-9_]+)`?\s*$"
)

_NEW_FILE_SECTION_RE = re.compile(
    r"(?:^|\n)(?:#{1,4}\s*(?:NEW\s+)?FILE\s*:\s*`?(?P<header_path>[A-Za-z0-9_./-]+\.[A-Za-z0-9_]+)`?"
    r"[ \t]*\n\s*```[a-zA-Z0-9_-]*[ \t]*\n(?P<header_body>.*?)\n```"
    r"|```[a-zA-Z0-9_-]+(?:\s+|:)(?P<fence_path>[A-Za-z0-9_./-]+\.[A-Za-z0-9_]+)[ \t]*\n(?P<fence_body>.*?)\n```)",
    re.DOTALL,
)


def _normalize_path_prefixes(
    body: str,
    *,
    known_files: Iterable[str] | None = None,
    project: str | Path | None = None,
) -> str:
    """Normalize path prefixes if files match known files or exist under project/src/."""
    candidates: set[str] = set(str(f) for f in (known_files or ()))
    if project:
        try:
            proj_p = Path(project)
            if proj_p.is_dir():
                for entry in proj_p.iterdir():
                    if entry.is_file() and entry.name.startswith("."):
                        candidates.add(entry.name)
            src_p = proj_p / "src"
            if src_p.is_dir():
                for root, _, files in os.walk(src_p):
                    rel_dir = os.path.relpath(root, proj_p)
                    for f in files:
                        candidates.add(os.path.join(rel_dir, f))
        except Exception:
            pass

    if not candidates:
        return body

    def _strip_rel_prefix(p: str) -> str:
        return re.sub(r"^(?:\./)+", "", p.replace("\\", "/")).lstrip("/")

    src_map: dict[str, str] = {}
    basename_counts: dict[str, int] = {}
    for f in candidates:
        f_norm = _strip_rel_prefix(f)
        base = f_norm.rsplit("/", 1)[-1]
        basename_counts[base] = basename_counts.get(base, 0) + 1

    proj_root = Path(project) if project else None
    for f in candidates:
        f_norm = _strip_rel_prefix(f)
        if f_norm.startswith(".") and len(f_norm) > 1 and "/" not in f_norm:
            dotless = f_norm[1:]
            if proj_root is None or not (proj_root / dotless).exists():
                src_map.setdefault(dotless, f_norm)
        if f_norm.startswith("src/"):
            src_map[f_norm[4:]] = f_norm
        if "/" in f_norm:
            suffix = f_norm.split("/", 1)[1]
            if proj_root is None or not (proj_root / suffix).exists():
                src_map.setdefault(suffix, f_norm)
            base = f_norm.rsplit("/", 1)[-1]
            if basename_counts.get(base) == 1 and (proj_root is None or not (proj_root / base).exists()):
                src_map.setdefault(base, f_norm)

    if not src_map:
        return body

    def _replace_git_header(m: re.Match) -> str:
        old = m.group("old")
        new = m.group("new")
        old_norm = src_map.get(old, old)
        new_norm = src_map.get(new, new)
        return f"diff --git a/{old_norm} b/{new_norm}"

    def _replace_old_file_header(m: re.Match) -> str:
        path = m.group(1)
        return f"--- a/{src_map.get(path, path)}"

    def _replace_new_file_header(m: re.Match) -> str:
        path = m.group(1)
        return f"+++ b/{src_map.get(path, path)}"

    body = re.sub(
        r"^diff --git a/(?P<old>.+?) b/(?P<new>.+?)[ \t]*$",
        _replace_git_header,
        body,
        flags=re.MULTILINE,
    )
    body = re.sub(r"^--- a/(\S+)", _replace_old_file_header, body, flags=re.MULTILINE)
    body = re.sub(r"^\+\+\+ b/(\S+)", _replace_new_file_header, body, flags=re.MULTILINE)
    return body


def _resolve_candidate_path(
    raw_path: str,
    project_path: Path | None,
    known_list: list[str],
) -> str:
    cleaned = raw_path.strip().strip("`'\"").replace("\\", "/")
    if cleaned.startswith(("a/", "b/")):
        cleaned = cleaned[2:]
    cleaned = re.sub(r"^(?:\./)+", "", cleaned).lstrip("/")
    if project_path is not None:
        if (project_path / cleaned).exists():
            return cleaned
        if (project_path / "src" / cleaned).exists():
            return f"src/{cleaned}"
    for k in known_list:
        k_norm = k.replace("\\", "/")
        if k_norm == cleaned or k_norm.endswith(f"/{cleaned}"):
            return k_norm
    return cleaned


def _apply_search_replace_to_text(content: str, search: str, replace: str) -> str | None:
    """Apply one SEARCH/REPLACE block to content, with whitespace-tolerant fallback."""
    if not search:
        return replace + ("\n" if replace and not replace.endswith("\n") else "")
    if search in content:
        return content.replace(search, replace, 1)

    content_lines = content.splitlines(keepends=True)
    search_lines = search.splitlines()
    replace_lines = replace.splitlines()
    if not search_lines:
        return None

    # Line-by-line rstrip match
    n = len(search_lines)
    search_rstrip = [s.rstrip() for s in search_lines]
    for i in range(len(content_lines) - n + 1):
        if [c.rstrip("\r\n").rstrip() for c in content_lines[i : i + n]] == search_rstrip:
            ending = "\n"
            if content_lines[i].endswith("\r\n"):
                ending = "\r\n"
            replacement_text = "".join(r + ending for r in replace_lines)
            return "".join(content_lines[:i]) + replacement_text + "".join(content_lines[i + n :])

    # Line-by-line strip match (ignoring leading/trailing whitespace differences)
    search_strip = [s.strip() for s in search_lines if s.strip()]
    if search_strip:
        for i in range(len(content_lines) - n + 1):
            window_strip = [c.strip() for c in content_lines[i : i + n] if c.strip()]
            if window_strip == search_strip:
                ending = "\n"
                replacement_text = "".join(r + ending for r in replace_lines)
                return "".join(content_lines[:i]) + replacement_text + "".join(content_lines[i + n :])
    return None


def _format_unified_diff_for_file(rel_path: str, old_text: str | None, new_text: str) -> str:
    rel_norm = re.sub(r"^(?:\./)+", "", rel_path.replace("\\", "/")).lstrip("/")
    new_lines = new_text.splitlines()
    if old_text is None:
        if not new_lines:
            return (
                f"diff --git a/{rel_norm} b/{rel_norm}\n"
                "new file mode 100644\n"
                "--- /dev/null\n"
                f"+++ b/{rel_norm}\n"
            )
        body = "\n".join(f"+{line}" for line in new_lines)
        return (
            f"diff --git a/{rel_norm} b/{rel_norm}\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            f"+++ b/{rel_norm}\n"
            f"@@ -0,0 +1,{len(new_lines)} @@\n"
            f"{body}\n"
        )

    old_lines = old_text.splitlines()
    if old_lines == new_lines:
        return ""
    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{rel_norm}",
            tofile=f"b/{rel_norm}",
            lineterm="",
        )
    )
    if not diff_lines:
        return ""
    return f"diff --git a/{rel_norm} b/{rel_norm}\n" + "\n".join(diff_lines) + "\n"


def synthesize_diff_from_search_replace(
    text: str,
    project: Path | str | None,
    known_files: Iterable[str] | None = None,
) -> str:
    """Synthesize a valid git unified diff from SEARCH/REPLACE and new-file blocks."""
    if not text or project is None:
        return ""
    project_path = Path(project)
    known_list = [str(f) for f in (known_files or ())]

    has_sr = bool(_SEARCH_REPLACE_RE.search(text))
    has_new_file = bool(_NEW_FILE_SECTION_RE.search(text))
    if not has_sr and not has_new_file:
        # Fallback: when a single known target file is being edited and the model
        # emitted a full-file replacement inside a code fence instead of a diff.
        if len(known_list) == 1 and not _DIFF_START_RE.search(text):
            rel = _resolve_candidate_path(known_list[0], project_path, known_list)
            disk_file = project_path / rel
            if disk_file.is_file():
                try:
                    orig_text = disk_file.read_text(encoding="utf-8")
                except OSError:
                    orig_text = ""
                orig_lines = orig_text.splitlines()
                for m_fence in _FENCE_RE.finditer(text):
                    candidate_body = m_fence.group("body").strip("\r\n")
                    cand_lines = candidate_body.splitlines()
                    if len(cand_lines) < max(3, int(len(orig_lines) * 0.4)):
                        continue
                    if rel.endswith(".py"):
                        import ast

                        try:
                            ast.parse(candidate_body)
                        except SyntaxError:
                            continue
                    # Verify some structural overlap with the original file
                    orig_set = {line.strip() for line in orig_lines if len(line.strip()) > 6}
                    cand_set = {line.strip() for line in cand_lines if len(line.strip()) > 6}
                    if orig_set and len(orig_set & cand_set) / max(1, min(len(orig_set), len(cand_set))) >= 0.25:
                        return _format_unified_diff_for_file(rel, orig_text, candidate_body + "\n")
        return ""

    file_states: dict[str, tuple[str | None, str]] = {}

    def _get_current(rel: str) -> tuple[str | None, str]:
        if rel in file_states:
            return file_states[rel]
        disk_file = project_path / rel
        if disk_file.is_file():
            try:
                orig = disk_file.read_text(encoding="utf-8")
            except OSError:
                orig = ""
            file_states[rel] = (orig, orig)
        else:
            file_states[rel] = (None, "")
        return file_states[rel]

    if has_sr:
        last_end = 0
        current_path: str | None = None
        for match in _SEARCH_REPLACE_RE.finditer(text):
            preceding = text[last_end : match.start()]
            last_end = match.end()
            for raw_line in reversed(preceding.splitlines()):
                line = raw_line.strip()
                if not line or line.startswith("```"):
                    if line.startswith("```"):
                        parts = line.lstrip("`").strip().split()
                        if len(parts) >= 2 and "." in parts[-1]:
                            current_path = _resolve_candidate_path(parts[-1], project_path, known_list)
                            break
                        if len(parts) == 1 and ("/" in parts[0] or "." in parts[0]):
                            current_path = _resolve_candidate_path(parts[0], project_path, known_list)
                            break
                    continue
                m_hdr = _FILE_HEADER_LINE_RE.match(line)
                if m_hdr:
                    current_path = _resolve_candidate_path(m_hdr.group("path"), project_path, known_list)
                    break

            target_rel = current_path
            if not target_rel and len(known_list) == 1:
                target_rel = _resolve_candidate_path(known_list[0], project_path, known_list)
            if not target_rel:
                # Probe all known_files to see which one contains the search block
                search_body = match.group("search")
                for candidate in known_list:
                    cand_rel = _resolve_candidate_path(candidate, project_path, known_list)
                    orig, cur = _get_current(cand_rel)
                    if (
                        orig is not None
                        and _apply_search_replace_to_text(cur, search_body, match.group("replace")) is not None
                    ):
                        target_rel = cand_rel
                        break
            if not target_rel:
                continue

            orig, cur = _get_current(target_rel)
            updated = _apply_search_replace_to_text(cur, match.group("search"), match.group("replace"))
            if updated is not None:
                file_states[target_rel] = (orig, updated)

    if has_new_file:
        for m_nf in _NEW_FILE_SECTION_RE.finditer(text):
            raw_p = m_nf.group("header_path") or m_nf.group("fence_path")
            body = m_nf.group("header_body") if m_nf.group("header_path") else m_nf.group("fence_body")
            if not raw_p or body is None:
                continue
            if _SEARCH_REPLACE_RE.search(body) or _DIFF_START_RE.search(body):
                continue
            rel = _resolve_candidate_path(raw_p, project_path, known_list)
            if rel in file_states:
                continue
            orig, _ = _get_current(rel)
            new_content = body + ("\n" if not body.endswith("\n") else "")
            file_states[rel] = (orig, new_content)

    diffs: list[str] = []
    for rel, (orig, updated) in file_states.items():
        piece = _format_unified_diff_for_file(rel, orig, updated)
        if piece:
            diffs.append(piece)
    return "".join(diffs)


def _find_top_level_constant_insert_pos(working: list[str]) -> int:
    """Find a clean module-level insertion line after docstring and imports."""
    idx = 0
    n = len(working)
    while idx < n and (not working[idx].strip() or working[idx].strip().startswith("#")):
        idx += 1
    if idx < n and working[idx].lstrip().startswith(('"""', "'''")):
        quote = working[idx].lstrip()[:3]
        if working[idx].lstrip()[3:].count(quote) == 0:
            idx += 1
            while idx < n and quote not in working[idx]:
                idx += 1
        idx += 1
    last_import_end = idx
    in_parens = False
    while idx < n:
        stripped = working[idx].strip()
        if in_parens:
            if ")" in stripped:
                in_parens = False
            idx += 1
            last_import_end = idx
            continue
        if not stripped or stripped.startswith("#"):
            idx += 1
            continue
        if stripped.startswith(("import ", "from ")):
            if "(" in stripped and ")" not in stripped:
                in_parens = True
            idx += 1
            last_import_end = idx
            continue
        break
    return last_import_end


def _apply_edit_subblocks_fallback(
    working: list[str],
    new_chunk_template: list[tuple[str, str]],
    expected_start: int,
) -> tuple[list[str], bool]:
    """Decompose a hunk whose full context failed to match into atomic (-/+) edit blocks
    and apply each one against *working* using nearest-context or unique-line anchoring."""
    changed_any = False
    i = 0
    n_tpl = len(new_chunk_template)
    pre_ctx: list[str] = []

    while i < n_tpl:
        kind, text = new_chunk_template[i]
        if kind == " ":
            pre_ctx.append(text)
            i += 1
            continue

        removed: list[str] = []
        added: list[str] = []
        while i < n_tpl and new_chunk_template[i][0] in ("-", "+"):
            k, t = new_chunk_template[i]
            if k == "-":
                removed.append(t)
            else:
                added.append(t)
            i += 1

        post_ctx: list[str] = []
        j = i
        while j < n_tpl and new_chunk_template[j][0] == " " and len(post_ctx) < 3:
            post_ctx.append(new_chunk_template[j][1])
            j += 1

        if removed:
            rem_n = len(removed)
            rem_strip = [r.strip() for r in removed]
            best_idx: int | None = None
            best_score: tuple[int, int] = (-1, -(len(working) + 1000))

            for cand in range(len(working) - rem_n + 1):
                if [w.strip() for w in working[cand : cand + rem_n]] == rem_strip:
                    ctx_hits = 0
                    if pre_ctx and cand >= 1 and working[cand - 1].strip() == pre_ctx[-1].strip():
                        ctx_hits += 2
                    if len(pre_ctx) >= 2 and cand >= 2 and working[cand - 2].strip() == pre_ctx[-2].strip():
                        ctx_hits += 1
                    if (
                        post_ctx
                        and cand + rem_n < len(working)
                        and working[cand + rem_n].strip() == post_ctx[0].strip()
                    ):
                        ctx_hits += 2
                    if (
                        len(post_ctx) >= 2
                        and cand + rem_n + 1 < len(working)
                        and working[cand + rem_n + 1].strip() == post_ctx[1].strip()
                    ):
                        ctx_hits += 1
                    exact_bonus = 1 if working[cand : cand + rem_n] == removed else 0
                    score = (ctx_hits * 2 + exact_bonus, -abs(cand - expected_start))
                    if score > best_score:
                        best_score = score
                        best_idx = cand

            if best_idx is not None:
                working[best_idx : best_idx + rem_n] = added
                expected_start = best_idx + len(added)
                changed_any = True
            elif len(removed) == len(added) and len(removed) > 1:
                # Non-contiguous removed lines bundled into one block: apply line by line
                for r_line, a_line in zip(removed, added, strict=False):
                    r_s = r_line.strip()
                    if not r_s:
                        continue
                    line_idx: int | None = None
                    best_dist = len(working) + 1000
                    for cand, w_line in enumerate(working):
                        if w_line.strip() == r_s:
                            dist = abs(cand - expected_start)
                            if dist < best_dist:
                                best_dist = dist
                                line_idx = cand
                    if line_idx is not None:
                        working[line_idx] = a_line
                        expected_start = line_idx + 1
                        changed_any = True
            else:
                # Check if added lines are already present (duplicate hunk)
                add_strip = [a.strip() for a in added if a.strip()]
                if add_strip:
                    w_strips = {w.strip() for w in working}
                    if all(a_s in w_strips for a_s in add_strip):
                        changed_any = True
        elif added:
            # Pure addition block
            add_n = len(added)
            add_strip = [a.strip() for a in added]
            already_present = any(
                [w.strip() for w in working[cand : cand + add_n]] == add_strip
                for cand in range(max(0, len(working) - add_n + 1))
            )
            if already_present:
                changed_any = True
            else:
                ins_pos: int | None = None
                if pre_ctx:
                    anchor = pre_ctx[-1].strip()
                    if anchor:
                        best_dist = len(working) + 1000
                        for cand, w_line in enumerate(working):
                            if w_line.strip() == anchor:
                                dist = abs(cand + 1 - expected_start)
                                if dist < best_dist:
                                    best_dist = dist
                                    ins_pos = cand + 1
                if ins_pos is None and post_ctx:
                    anchor = post_ctx[0].strip()
                    if anchor:
                        best_dist = len(working) + 1000
                        for cand, w_line in enumerate(working):
                            if w_line.strip() == anchor:
                                dist = abs(cand - expected_start)
                                if dist < best_dist:
                                    best_dist = dist
                                    ins_pos = cand
                if ins_pos is None and expected_start <= 30:
                    ins_pos = _find_top_level_constant_insert_pos(working)
                if ins_pos is not None:
                    working[ins_pos:ins_pos] = added
                    expected_start = ins_pos + len(added)
                    changed_any = True

        pre_ctx = []

    return working, changed_any


def _apply_hunks_with_fuzzy_fallback(
    orig_lines: list[str], hunk_blocks: list[list[str]]
) -> tuple[list[str], bool] | None:
    """Apply parsed hunk bodies to orig_lines; return (new_lines, used_fuzzy) or None."""
    working = list(orig_lines)
    offset = 0
    used_fuzzy = False
    applied_any = False

    for hunk in hunk_blocks:
        if not hunk:
            continue
        m = _HUNK_RE.match(hunk[0])
        expected_start = (int(m.group("old_start")) - 1 + offset) if m else 0
        old_chunk: list[str] = []
        new_chunk_template: list[tuple[str, str]] = []
        for line in hunk[1:]:
            if line.startswith("\\"):
                continue
            if line.startswith("-"):
                old_chunk.append(line[1:])
                new_chunk_template.append(("-", line[1:]))
            elif line.startswith("+"):
                new_chunk_template.append(("+", line[1:]))
            elif line.startswith(" "):
                old_chunk.append(line[1:])
                new_chunk_template.append((" ", line[1:]))
            else:
                old_chunk.append(line)
                new_chunk_template.append((" ", line))

        if not old_chunk:
            insert_pos = max(0, min(len(working), expected_start))
            added = [text for kind, text in new_chunk_template if kind != "-"]
            working[insert_pos:insert_pos] = added
            offset += len(added)
            applied_any = True
            continue

        n = len(old_chunk)
        match_pos: int | None = None
        if 0 <= expected_start <= len(working) - n and working[expected_start : expected_start + n] == old_chunk:
            match_pos = expected_start
        else:
            used_fuzzy = True
            # Search outward from expected_start for exact match
            best_dist = len(working) + 1
            for i in range(len(working) - n + 1):
                if working[i : i + n] == old_chunk:
                    dist = abs(i - expected_start)
                    if dist < best_dist:
                        best_dist = dist
                        match_pos = i
            # Rstrip match
            if match_pos is None:
                old_rstrip = [x.rstrip() for x in old_chunk]
                for i in range(len(working) - n + 1):
                    if [w.rstrip() for w in working[i : i + n]] == old_rstrip:
                        dist = abs(i - expected_start)
                        if dist < best_dist:
                            best_dist = dist
                            match_pos = i
            # Strip match
            if match_pos is None:
                old_strip = [x.strip() for x in old_chunk]
                for i in range(len(working) - n + 1):
                    if [w.strip() for w in working[i : i + n]] == old_strip:
                        dist = abs(i - expected_start)
                        if dist < best_dist:
                            best_dist = dist
                            match_pos = i

        if match_pos is not None and match_pos >= 0:
            matched_disk_lines = working[match_pos : match_pos + n]
            disk_iter = iter(matched_disk_lines)
            replacement: list[str] = []
            for kind, text in new_chunk_template:
                if kind == " ":
                    replacement.append(next(disk_iter, text))
                elif kind == "-":
                    next(disk_iter, None)
                elif kind == "+":
                    replacement.append(text)
            working[match_pos : match_pos + n] = replacement
            offset += len(replacement) - n
            applied_any = True
            continue

        # Fallback: decompose the hunk into atomic edit subblocks
        working, sub_applied = _apply_edit_subblocks_fallback(
            working, new_chunk_template, max(0, expected_start)
        )
        if sub_applied:
            used_fuzzy = True
            applied_any = True
            offset = len(working) - len(orig_lines)

    if not applied_any:
        return None
    return working, used_fuzzy


def _repair_diff_against_project(diff: str, project: Path | str) -> str:
    """When a unified diff has inaccurate hunk line numbers, context lines, or
    multiple diff sections targeting the same file, re-anchor and merge hunks
    against the actual files in *project* via difflib."""
    proj_path = Path(project)
    lines = diff.splitlines()
    sections: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("diff --git ") and current:
            sections.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append(current)

    # Group sections touching the same existing file so multiple diff --git blocks
    # for the same path are merged into one clean unified diff.
    grouped_hunks: dict[str, list[list[str]]] = {}
    grouped_raw: dict[str, list[list[str]]] = {}
    section_order: list[tuple[str, str | list[str]]] = []

    for sec in sections:
        header_match = _GIT_HEADER_RE.match(sec[0]) if sec else None
        if not header_match:
            section_order.append(("raw", sec))
            continue
        old_rel = header_match.group("old")
        new_rel = header_match.group("new")
        is_new_or_del = any(
            sec_line.startswith(("new file mode", "deleted file mode", "--- /dev/null", "+++ /dev/null"))
            for sec_line in sec[:6]
        ) or any(sec_line.startswith("@@ -0,0") for sec_line in sec)
        target_file = proj_path / old_rel
        if is_new_or_del or old_rel != new_rel:
            section_order.append(("raw", sec))
            continue
        if not target_file.is_file():
            section_order.append(("missing_raw", sec))
            continue

        hunks: list[list[str]] = []
        cur_hunk: list[str] = []
        for sec_line in sec:
            if sec_line.startswith("@@"):
                if cur_hunk:
                    hunks.append(cur_hunk)
                cur_hunk = [sec_line]
            elif cur_hunk:
                cur_hunk.append(sec_line)
        if cur_hunk:
            hunks.append(cur_hunk)
        if not hunks:
            section_order.append(("missing_raw", sec))
            continue

        if old_rel not in grouped_hunks:
            grouped_hunks[old_rel] = []
            grouped_raw[old_rel] = []
            section_order.append(("file", old_rel))
        grouped_hunks[old_rel].extend(hunks)
        grouped_raw[old_rel].append(sec)

    repaired_sections: list[str] = []
    fallback_sections: list[str] = []
    for kind, item in section_order:
        if kind == "raw":
            assert isinstance(item, list)
            chunk = "\n".join(item) + "\n"
            repaired_sections.append(chunk)
            fallback_sections.append(chunk)
            continue
        if kind == "missing_raw":
            assert isinstance(item, list)
            fallback_sections.append("\n".join(item) + "\n")
            continue

        old_rel = str(item)
        raw_secs = grouped_raw[old_rel]
        all_hunks = grouped_hunks[old_rel]
        target_file = proj_path / old_rel
        try:
            orig_text = target_file.read_text(encoding="utf-8")
        except OSError:
            for s in raw_secs:
                fallback_sections.append("\n".join(s) + "\n")
            continue

        orig_lines = orig_text.splitlines()
        applied = _apply_hunks_with_fuzzy_fallback(orig_lines, all_hunks)
        if applied is None:
            for s in raw_secs:
                fallback_sections.append("\n".join(s) + "\n")
            continue
        new_lines, used_fuzzy = applied
        if not used_fuzzy and len(raw_secs) == 1:
            chunk = "\n".join(raw_secs[0]) + "\n"
            repaired_sections.append(chunk)
            fallback_sections.append(chunk)
            continue
        regenerated = _format_unified_diff_for_file(old_rel, orig_text, "\n".join(new_lines) + "\n")
        if regenerated:
            repaired_sections.append(regenerated)
            fallback_sections.append(regenerated)
        else:
            for s in raw_secs:
                fallback_sections.append("\n".join(s) + "\n")

    if repaired_sections:
        return "".join(repaired_sections)
    return "".join(fallback_sections)


def extract_unified_diff(
    text: str,
    *,
    known_files: Iterable[str] | None = None,
    project: str | Path | None = None,
) -> str | None:
    """Pull a unified diff out of an agent's stdout.

    Agents habitually wrap diffs in code fences and add commentary, so accept
    both fenced and bare output. When *project* is provided, also supports
    SEARCH/REPLACE synthesis and fuzzy hunk repair against on-disk files.
    Returns None when the reply contains no diff, which includes the explicit
    ``NO-PATCH:`` refusal.
    """
    if not text:
        return None
    if project is not None and _SEARCH_REPLACE_RE.search(text):
        synthesized = synthesize_diff_from_search_replace(text, project, known_files=known_files)
        if synthesized:
            return synthesized
    # Fix split hunk headers produced by some models: @@ -\n<nums> @@
    text = re.sub(r"@@ -[ \t]*\n[ \t]*(\d+)", r"@@ -\1", text)
    # Fix common path hallucination: project/analysis/toon.yaml -> project/analysis.toon.yaml
    text = re.sub(r"([ab]/project/analysis)/toon\.yaml", r"\1.toon.yaml", text)
    text = re.sub(r"(project/analysis)/toon\.yaml", r"\1.toon.yaml", text)
    text = re.sub(r"([ab]/)analysis/toon\.yaml", r"\1project/analysis.toon.yaml", text)
    text = re.sub(r"(?<![/\w])analysis/toon\.yaml", r"project/analysis.toon.yaml", text)
    if known_files or project:
        text = _normalize_path_prefixes(text, known_files=known_files, project=project)

    fenced_diffs: list[str] = []
    for match in _FENCE_RE.finditer(text):
        body = match.group("body")
        if _DIFF_START_RE.search(body):
            start = _DIFF_START_RE.search(body)
            assert start is not None
            fenced_diffs.append(_normalize_diff(body[start.start() :]))
    if fenced_diffs:
        combined = "".join(fenced_diffs)
        if project is not None:
            combined = _repair_diff_against_project(combined, project)
        return combined

    if _DIFF_START_RE.search(text):
        start = _DIFF_START_RE.search(text)
        assert start is not None
        normalized = _normalize_diff(text[start.start() :])
        if project is not None:
            normalized = _repair_diff_against_project(normalized, project)
        return normalized

    if project is not None:
        synthesized = synthesize_diff_from_search_replace(text, project, known_files=known_files)
        if synthesized:
            return synthesized
    return None


_ELLIPSIS_RE = re.compile(r"^\s*(?:\.{3,}|//\s*\.{3,}|\.\.\.\s*\[truncated\])\s*$")
_STRAY_INNER_HEADER_RE = re.compile(r"^[+-]?(?:--- (?:a/\S+|/dev/null)|\+\+\+ (?:b/\S+|/dev/null))\s*$")


def _sanitize_inner_headers(lines: list[str]) -> list[str]:
    """Strip duplicate or nested diff/file headers leaked inside hunks,
    discard model ellipses (`...`), and fix context lines missing leading spaces.

    Models occasionally emit a second diff header or copy ``--- a/...``/``+++ b/...``
    inside a hunk body, or insert ``...`` placeholders, causing git apply to
    immediately abort with 'corrupt patch'.
    """
    cleaned: list[str] = []
    in_hunk = False
    after_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_hunk = False
            after_fence = True
            continue
        if line.startswith("diff --git "):
            in_hunk = False
            after_fence = False
            cleaned.append(line)
            continue
        if after_fence:
            if line.startswith(("--- a/", "--- /dev/null", "+++ b/", "+++ /dev/null", "@@")):
                after_fence = False
            else:
                continue
        if line.startswith("@@"):
            in_hunk = True
            cleaned.append(line)
            continue
        if line.startswith(
            ("index ", "new file mode", "deleted file mode", "similarity index", "rename from", "rename to")
        ):
            in_hunk = False
            cleaned.append(line)
            continue
        if in_hunk:
            if _STRAY_INNER_HEADER_RE.match(line.lstrip()):
                continue
            if _ELLIPSIS_RE.match(line):
                continue
            # If inside a hunk and line doesn't start with +, -, \, or space:
            # Models sometimes emit context lines without a leading space or with a stray leading dot.
            if not line.startswith(("+", "-", " ", "\\")):
                if line.startswith(". ") or re.match(r"^\.[A-Z_][A-Z0-9_]*(?:\[\d+\])?\s*:", line):
                    line = " " + line[1:]
                else:
                    line = " " + line
        cleaned.append(line)
    return cleaned


def _normalize_diff(body: str) -> str:
    """Trim trailing fences/prose and guarantee the single trailing newline
    ``git apply`` expects."""
    lines = body.splitlines()
    while lines and lines[-1].strip() in {"", "```"}:
        lines.pop()
    return "\n".join(_repair_hunk_counts(_repair_missing_file_headers(_sanitize_inner_headers(lines)))) + "\n"


def _repair_hunk_counts(lines: list[str]) -> list[str]:
    """Recompute ``@@`` line counts from the hunk body.

    Models miscount hunk lengths routinely — one line off makes ``git apply``
    reject the whole patch as "corrupt patch at line N". The body is the
    authoritative content and the counts are derived from it, so recomputing
    them is a safe normalisation rather than a guess.
    """
    repaired = list(lines)
    for index, line in enumerate(repaired):
        match = _HUNK_RE.match(line)
        if not match:
            continue
        old_count = 0
        new_count = 0
        for body_line in repaired[index + 1 :]:
            if body_line.startswith(("@@", "diff --git", "--- a/", "--- /dev/null", "+++ b/", "+++ /dev/null")):
                break
            if body_line.startswith("\\"):  # "\ No newline at end of file"
                continue
            if body_line.startswith("+"):
                new_count += 1
            elif body_line.startswith("-"):
                old_count += 1
            else:  # context line (a bare empty line counts as context too)
                old_count += 1
                new_count += 1
        repaired[index] = (
            f"@@ -{match.group('old_start')},{old_count} "
            f"+{match.group('new_start')},{new_count} @@{match.group('tail')}"
        )
    return repaired


def _repair_missing_file_headers(lines: list[str]) -> list[str]:
    """Insert ``---``/``+++`` lines when an agent omits them.

    Models routinely emit a ``diff --git`` header followed straight by a
    ``@@`` hunk (or ``new file mode`` + ``@@``), which ``git apply`` rejects
    as "patch fragment without header". The paths are already in the
    ``diff --git`` line, so the headers can be reconstructed deterministically
    rather than by re-prompting.
    """
    repaired: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        repaired.append(line)
        match = _GIT_HEADER_RE.match(line)
        if not match:
            i += 1
            continue

        # Scan metadata lines between `diff --git` and the first `@@` or next `diff --git`
        is_new_file = False
        is_deleted_file = False
        has_old_header = False
        has_new_header = False
        j = i + 1
        while j < n:
            cand = lines[j]
            if cand.startswith("diff --git ") or cand.startswith("@@"):
                break
            if cand.startswith("new file mode"):
                is_new_file = True
            elif cand.startswith("deleted file mode"):
                is_deleted_file = True
            elif cand.startswith("--- "):
                has_old_header = True
            elif cand.startswith("+++ "):
                has_new_header = True
            repaired.append(cand)
            j += 1

        if j < n and lines[j].startswith("@@"):
            hunk_line = lines[j]
            if hunk_line.startswith("@@ -0,0"):
                is_new_file = True
            elif "+0,0 @@" in hunk_line or re.search(r"\+0(?:,0)?\s*@@", hunk_line):
                is_deleted_file = True

            if not has_old_header:
                repaired.append("--- /dev/null" if is_new_file else f"--- a/{match.group('old')}")
            if not has_new_header:
                repaired.append("+++ /dev/null" if is_deleted_file else f"+++ b/{match.group('new')}")
        i = j
    return repaired


def symlink_creations(diff: str) -> bool:
    """Whether a diff creates a symlink or converts a file into one.

    ``git apply`` rejects ``../`` paths but happily creates a link pointing
    anywhere on the filesystem, which hands an agent-authored patch a way out
    of the workspace it was scoped to. Legitimate uses exist, so this is a
    policy question rather than a hard error — see ``symlinks_allowed``.
    """
    return bool(_SYMLINK_MODE_RE.search(diff))
