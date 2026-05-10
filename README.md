# koru

Python package for **closed-loop** automation in `semcod/*` repositories.

The name refers to *Koru* (Māori spiral), matching a "spiraling loop" refactor flow.

## Install (editable)

```bash
pip install -e .
```

## Usage

Run one command across matching repositories and retry failures in a closed loop:

```bash
koru-loop \
  --workspace /path/to/repos \
  --include "semcod/*" \
  --command "python -m pytest -q"
```
