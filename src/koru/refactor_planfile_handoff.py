"""Text handoff for IDE LLMs: draft planfile refactor tickets from code2llm analysis."""

from __future__ import annotations

from pathlib import Path


def render_planfile_refactor_handoff(project: Path) -> str:
    """Return markdown instructions + paths (stdout → paste into IDE chat)."""
    root = project.resolve()
    primary = root / "project" / "analysis.toon.yaml"
    fallback = root / "analysis.toon.yaml"
    if primary.is_file():
        analysis_path, analysis_display = primary, "project/analysis.toon.yaml"
    elif fallback.is_file():
        analysis_path, analysis_display = fallback, "analysis.toon.yaml"
    else:
        analysis_path, analysis_display = primary, "project/analysis.toon.yaml"
    prompt_txt = root / "project" / "prompt.txt"
    prompt_hint = ""
    if prompt_txt.is_file():
        try:
            pr = prompt_txt.relative_to(root)
        except ValueError:
            pr = prompt_txt
        prompt_hint = f"- Also open `{pr}` (refactor brief).\n"
    exists = "tak" if analysis_path.is_file() else "nie — wygeneruj np. `code2llm` / task semcod"
    return (
        "## Planfile: tickety refaktoryzacji (z analizy)\n\n"
        f"- Plik analizy: `{analysis_display}` (w repo: **{exists}**).\n"
        f"- Pełna ścieżka: `{analysis_path}`\n"
        f"{prompt_hint}"
        "- W IDE: **dołącz** (`@`) powyższy plik analizy do czatu "
        "albo wklej fragmenty REFACTOR / HEALTH.\n"
        "- Dla każdej sensownej jednostki pracy utwórz **osobny** ticket planfile"
        " (queue `default` lub wg projektu), "
        "z etykietą `llm-ready`, krótkim tytułem i opisem z odwołaniem do ścieżek"
        " plików z analizy.\n"
        "- Po utworzeniu: `task tickets:next` / `planfile` — tak, by kolejka"
        " `koru autonomous` miała co wykonać.\n"
        "- Szybki skan ticketów z artefaktów (gdy analiza jest na miejscu): "
        "`koru scan --apply --semcod-artifacts`.\n"
    )


__all__ = ["render_planfile_refactor_handoff"]
