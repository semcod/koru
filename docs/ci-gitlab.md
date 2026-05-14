# CI na GitLabie (szablon „thin smoke”)

Ten plik jest **lustrem** dokumentacji GitHub Actions ([`ci-github.md`](./ci-github.md)): ten sam zestaw kroków co w [`.github/workflows/koru-ci.yml`](../.github/workflows/koru-ci.yml) — Python 3.12, `pip install -e ".[dev]"`, `ruff` na `src/koru`, szybki `pytest`, smoke CLI (`koru --help`, `python -m koru --doctor --project .`).

Nie wymaga GitLab App ani custom integracji; wystarczy zwykły pipeline w projekcie.

## Co skopiować

1. Pobierz przykładowy plik z repozytorium **koru**:

   - źródło: [`examples/ci/gitlab-ci.example.yml`](../examples/ci/gitlab-ci.example.yml)  
   - surowy YAML (np. do podglądu w przeglądarce):  
     `https://raw.githubusercontent.com/semcod/koru/main/examples/ci/gitlab-ci.example.yml`

2. Skopiuj zawartość do **`.gitlab-ci.yml`** w katalogu głównym swojego projektu (lub dołącz jako [`include`](https://docs.gitlab.com/ee/ci/yaml/#include) po dostosowaniu ścieżek).

3. Dostosuj kroki tak jak w [`ci-github.md`](./ci-github.md) — instalacja zależności, ścieżka `ruff`, zakres `pytest`, obecność entrypointu `koru`.

4. **Reguły uruchamiania**: w przykładzie pipeline na zdarzenia MR oraz ręczne (`web`). Możesz dodać `push` na chronione gałęzie, zgodnie z [workflow rules](https://docs.gitlab.com/ee/ci/yaml/#workflowrules).

## Pierwszy krok po sklonowaniu (Epic 8 / onboarding)

W katalogu z **koru** zainstalowanym z repozytorium:

```bash
koru init-ci
```

Wypisze ścieżkę workflow GitHub oraz link do dokumentacji CI; dla GitLab użyj tego pliku i powyższych kroków.

## Uwagi

- Pełne bramki planfile / regix to osobna warstwa (Taskfile lokalnie lub dodatkowe joby); ten szablon to **szybka** weryfikacja Pythona i CLI, analogicznie do `koru-ci.yml` na GitHubie.
- Dla [zewnętrznych status checks](https://docs.gitlab.com/ee/user/project/merge_requests/status_checks.html) przy MR planuj osobny epik (por. roadmapa — GitHub/GitLab App).
