# mdflow — Markdown dependency analyzer

## Co to jest

`mdflow` (PyPI: `mdflow>=0.1.6`) parsuje Markdown files i wyciąga
**wszystkie structural elements**: headings, links, fenced code blocks
(z `markpact:*` references), TOON/YAML quality sections, document metadata.

Output: **Mermaid diagrams**, **HTML reports**, **Markdown summaries**.

W koru używaj do **analizy zależności między dokumentami**:
SUMR.md ↔ workflows/ ↔ docs/ ↔ templates/.

## Kiedy używać

| Scenariusz | Komenda |
|---|---|
| Analyze single Markdown file | `mdflow analyze README.md` |
| Generate Mermaid diagram of doc graph | `mdflow graph docs/ --format mermaid` |
| HTML report o dokumentacji | `mdflow report docs/ -o report.html` |
| Find broken links | `mdflow validate docs/ --check-links` |
| Extract markpact references | `mdflow markpact-refs deployment.md` |

## Konfiguracja

### Brak osobnego configu

Wszystko CLI flags. Auto-detect markpact blocks, TOON sections, code fences.

## Komendy

```bash
mdflow --version
mdflow --help

# Single file
mdflow analyze README.md
mdflow analyze workflows/sumr-refresh-loop.md --format json

# Directory walk
mdflow analyze docs/ --recursive
mdflow report docs/ -o docs-report.html

# Diagrams
mdflow graph . --format mermaid -o deps.mmd
mdflow graph . --format dot -o deps.gv

# Validation
mdflow validate docs/ --check-links --check-fences
mdflow markpact-refs redeploy/local/deployment.md   # show all `markpact:ref`
```

## Integracja z koru

| Plik | Use case |
|---|---|
| `workflows/*.md` | Multi-step workflows — analyze cross-references |
| `redeploy/*/deployment.md` | markpact specs — `markpact-refs` validation |
| `docs/llm-tools/*/README.md` | per-tool docs — link health |
| SUMR.md | LLM snapshot — extract section dependencies |

```bash
# Find all markpact refs in deployment specs:
find redeploy -name '*.md' | xargs -I{} mdflow markpact-refs {}

# Check doc consistency:
mdflow validate docs/ workflows/ --check-links
```

## Reference

- Repo / PyPI: https://pypi.org/project/mdflow/
- Wersja: `mdflow==0.1.6`
- Companion: `sumd` (SUMR.md generation), `toonic` (TOON sections w doc)

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `mdflow: command not found` | `pip install --user --upgrade mdflow` |
| `markpact-refs` brak output | sprawdź syntax: \`\`\`bash markpact:ref name |
| Mermaid diagram bardzo duży | użyj `--scope <subdir>` lub `--max-depth 2` |
