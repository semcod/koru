"""Allow ``python -m koru`` (same as the ``koru`` console script)."""

from pathlib import Path

from koru.dotenv_loader import load_dotenv

load_dotenv(Path.cwd())

from koru.cli import main  # noqa: E402 — load .env before importing CLI modules.

if __name__ == "__main__":
    raise SystemExit(main())
