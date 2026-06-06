from __future__ import annotations

from koruapi.nlp2oql_bridge import nlp2oql_available, nlp2oql_run


def test_nlp2oql_run_plan_only_when_installed(tmp_path) -> None:
    if not nlp2oql_available():
        return

    result = nlp2oql_run(
        "sprawdź health endpoint",
        project_dir=str(tmp_path),
        execute=False,
    )
    assert "backend" in result
    assert result.get("backend") in {"testql", "nlp2cmd", "curllm"}
