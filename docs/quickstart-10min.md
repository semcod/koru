# Quickstart ~10 minut (koru w repozytorium)

Krótka ścieżka bez zmian w kodzie CLI: inicjalizacja projektu, podpowiedź CI i pierwszy „workflow” (ticket + bramka lokalna).

## Wymagania

- Python 3.12+
- Git
- Opcjonalnie [`task`](https://taskfile.dev/) jeśli w projekcie jest Taskfile (jak w szablonach semcod).

## 1. Zainstaluj koru z klonu

```bash
git clone https://github.com/semcod/koru.git
cd koru
python -m pip install -e ".[dev]"
koru --help
```

## 2. Zainicjalizuj planfile / `.koru` w **swoim** repozytorium docelowym

```bash
cd /ścieżka/do/twojego/projektu
koru --init
```

Jeśli katalog już był inicjalizowany i potrzebujesz nadpisać:

```bash
koru --init --force
```

## 3. CI — skopiuj thin smoke

- **GitHub:** postępuj według [`ci-github.md`](./ci-github.md) (plik `.github/workflows/koru-ci.yml`).
- **GitLab:** skopiuj [`examples/ci/gitlab-ci.example.yml`](../examples/ci/gitlab-ci.example.yml) do `.gitlab-ci.yml` — szczegóły w [`ci-gitlab.md`](./ci-gitlab.md).

Podpowiedź z CLI:

```bash
koru init-ci
```

## 4. Pierwszy workflow (ticket → praca → zamknięcie)

W katalogu projektu z Taskfile / planfile (dostosuj nazwy poleceń do swojego `Taskfile.yml`):

```bash
task tickets:next
# lub: planfile ticket next

# … implementacja (IDE / agent) …

task quality:regix:local
task test

task tickets:done -- PLF-XXX
```

### Automatyczne uruchamianie poleceń (np. `koru ci run`)

Sekcja `when:` w `koru.yaml` to głównie brief — żeby Koru **sam** wykonał shell,
dodaj ticket planfile z `executor.kind: shell` i uruchom kolejkę:

```bash
koru --queue --loop --project .
```

Pełna tabela mechanizmów: [`auto-execute-commands.md`](./auto-execute-commands.md).

Szczegóły cyklu życia ticketów: [`agent-guide.md`](./agent-guide.md), [`planfile-llm-guide.md`](./planfile-llm-guide.md).

## Dalej

- Autopilot IDE: [`autopilot-quickstart.md`](./autopilot-quickstart.md)
- Plugin probe: [`packages/coru/README.md`](../packages/coru/README.md) (`coru calibration`)
- Pełna lista dokumentacji: [`README.md`](./README.md) (ten katalog) · [`../README.md`](../README.md) (projekt)
- Scenariusze TestQL: [`../testql-scenarios/README.md`](../testql-scenarios/README.md)
- Szkice przyszłych przepisów koru (YAML, tylko dokumentacja): [`recipes/README.md`](./recipes/README.md)

## Szablony przepisów (opcjonalnie)

- Katalog **recipes** opisuje propozycje wersjonowanych „recept” — zacznij od
  [`recipes/README.md`](./recipes/README.md); same pliki YAML to na razie placeholdery
  do dyskusji w PR, nie ładują się automatycznie w parser koru.
