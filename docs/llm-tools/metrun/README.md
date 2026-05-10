# metrun — Execution Intelligence + Bottleneck Engine

## Co to jest

`metrun` (PyPI: `metrun>=0.1.31`) to **Python performance analysis library**
która turn raw profiling data w **intelligible execution report**:
bottleneck scores, dependency graphs, critical path highlighting,
**actionable fix suggestions** — wszystko w jednym tool.

Zamiast traditional profiler ("here is your data"), metrun mówi
*"here's the problem, here's the fix"*.

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Profile single function | `metrun profile <module.function>` |
| Profile pytest run | `metrun pytest tests/` |
| Bottleneck report z cProfile output | `metrun analyze profile.prof` |
| Critical path highlighting | `metrun path <profile> --critical` |
| Generate fix suggestions | `metrun suggest <profile>` |

## Konfiguracja

### Brak osobnego configu

CLI flags + auto-detect Python project (`pyproject.toml`).

## Komendy

```bash
metrun --version
metrun --help

# Profile + analyze
metrun profile myapp.process_request
metrun pytest tests/                       # full test suite profiling
metrun pytest tests/test_slow.py -k slow   # selective

# Analyze existing profile
metrun analyze profile.prof
metrun analyze profile.prof --top 10
metrun analyze profile.prof --format json -o report.json

# Bottleneck reports
metrun bottlenecks profile.prof
metrun path profile.prof --critical        # show critical path

# Fix suggestions
metrun suggest profile.prof                # actionable refactors
```

## Integracja z koru

| Plik | Use case |
|---|---|
| `Taskfile.yml` → `task quality:profile` | profile pytest run + generate report |
| `monitoring/prometheus/rules/app-alerts.yml` | trigger metrun na slow-endpoint alerts |
| Healing webhook | invoke `metrun analyze` przy SlowQueryDetected alerts |

## Reference

- Repo / PyPI: https://pypi.org/project/metrun/
- Wersja: `metrun==0.1.31`
- Companion: `regix` (regression metrics), profilery: cProfile, pyinstrument

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `metrun: command not found` | `pip install --user --upgrade metrun` |
| `analyze profile.prof` syntax error | sprawdź czy `.prof` faktycznie z cProfile (`python -m cProfile -o profile.prof script.py`) |
| `suggest` zwraca generic suggestions | `metrun suggest --context <module>` daje project-specific fixy |
