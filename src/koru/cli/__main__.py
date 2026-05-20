"""Allow ``python -m koru.cli`` when the ``cli`` package shadows ``cli.py``."""


from koru.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
