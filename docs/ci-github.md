# CI na GitHubie (szablon „thin smoke”)

Ten plik opisuje minimalny workflow **koru** pod adopcje w innych repozytoriach (Epic 2 — `koru-checks` / cienki CI). Nie wymaga GitHub App ani sekretów poza domyślnym `GITHUB_TOKEN` przy checkout.

## Co skopiować

1. Pobierz referencyjny plik z repozytorium **koru** (nazwa joba i kroki możesz zmienić):

   - źródło: [`.github/workflows/koru-ci.yml`](https://github.com/semcod/koru/blob/main/.github/workflows/koru-ci.yml)  
   - surowy YAML (np. `curl -O`):  
     `https://raw.githubusercontent.com/semcod/koru/main/.github/workflows/koru-ci.yml`

2. Umieść go w swoim projekcie jako `.github/workflows/koru-ci.yml` (lub inna nazwa).

3. Dostosuj kroki do swojego layoutu:

   - **`pip install`**: jeśli nie używasz `pyproject.toml` z extra `[dev]`, zamień na instalację własnych zależności testowych (np. `requirements-dev.txt`).
   - **Ruff**: uruchamiaj tylko jeśli masz `ruff` w dev-deps; w przeciwnym razie usuń ten krok. Ścieżka `src/koru` dotyczy tylko pakietu **koru** — u Ciebie np. `src/mypkg` lub `mypkg` w root.
   - **Pytest**: ogranicz ścieżki do szybkich testów (`tests/test_*.py`) albo znaczników (`-m "not slow"`), żeby PR nie czekał na cały zestaw integracyjny.
   - **CLI**: jeśli nie instalujesz **koru**, usuń krok „CLI smoke” albo zamień na `yourcli --help`.

4. **Wyzwalacze**: w szablonie PR i `workflow_dispatch`. Możesz dodać `push: branches: [main]` jak w pełnym CI koru ([`ci.yml`](https://github.com/semcod/koru/blob/main/.github/workflows/ci.yml) — macierz Python 3.12 / 3.13 i pełny `pytest`).

## Pierwszy krok po sklonowaniu (Epic 8 / onboarding)

W katalogu z **koru** zainstalowanym z repozytorium:

```bash
koru init-ci
```

Wypisze ścieżkę workflow w Twoim repozytorium po skopiowaniu pliku oraz link do tej dokumentacji.

## Uwagi

- Brak dodatkowych uprawnień: `permissions: contents: read` wystarcza do checkout publicznego / forków z tokenem domyślnym.
- Pełne bramki planfile / regix to osobna warstwa (Taskfile lokalnie lub własny job); ten workflow to szkielet **szybkiej** weryfikacji Pythona.
- GitLab: ten sam zestaw kroków opisuje **[`ci-gitlab.md`](./ci-gitlab.md)**.
