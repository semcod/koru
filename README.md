# koru


## AI Cost Tracking

![PyPI](https://img.shields.io/badge/pypi-costs-blue) ![Version](https://img.shields.io/badge/version-0.1.1-blue) ![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-Apache--2.0-green)
![AI Cost](https://img.shields.io/badge/AI%20Cost-$0.45-orange) ![Human Time](https://img.shields.io/badge/Human%20Time-2.0h-blue) ![Model](https://img.shields.io/badge/Model-openrouter%2Fqwen%2Fqwen3--coder--next-lightgrey)

- 🤖 **LLM usage:** $0.4500 (3 commits)
- 👤 **Human dev:** ~$200 (2.0h @ $100/h, 30min dedup)

Generated on 2026-05-10 using [openrouter/qwen/qwen3-coder-next](https://openrouter.ai/qwen/qwen3-coder-next)

---



Python package for **closed-loop** automation in `semcod/*` repositories.

The name refers to *Koru* (Māori spiral), matching a "spiraling loop" refactor flow.

## Install (editable)

```bash
pip install -e .
```

## Usage

Run one command across matching repositories and retry failures in a closed loop:

```bash
koru \
  --workspace /path/to/repos \
  --include "semcod/*" \
  --command "python -m pytest -q"
```


## License

Licensed under Apache-2.0.
