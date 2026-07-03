"""Interactive setup for shell LLM tools and API providers (``koru tillm``).

Full provider list comes from tillm's registry (most popular / newest first).
Flow: pick a provider from the list, paste a token (link to the token page is
printed; Enter keeps the existing token), pick a model from a select-list
(Enter keeps the current one), optionally make the provider the default for
every drive. All provider logic lives in tillm; this is only the koru-side UI.
"""

from __future__ import annotations

import getpass
import os
import sys

_ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "green": "\033[32m",
    "red": "\033[31m",
    "cyan": "\033[36m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
}


def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _c(text: str, *styles: str) -> str:
    if not _use_color():
        return text
    prefix = "".join(_ANSI[s] for s in styles)
    return f"{prefix}{text}{_ANSI['reset']}"


def _print_provider_table(specs, resolve_token, available_clients, default_provider) -> None:
    print()
    print(_c("Dostępne narzędzia / providerzy (tillm):", "bold"))
    print()
    header = f"  {'#':<3} {'provider':<12} {'typ':<13} {'token':<8} klienci (✓ = binarka w PATH)"
    print(_c(header, "dim"))
    print(_c("  " + "-" * (len(header) - 2), "dim"))
    for idx, spec in enumerate(specs, start=1):
        has_token = bool(resolve_token(spec.id)) or spec.kind == "local"
        token_state = _c("✓ jest", "green") if has_token else _c("✗ brak", "red")
        clients = ", ".join(
            (cid + (_c("✓", "green") if cid in available_clients else ""))
            for cid in spec.compatible_clients()
        ) or "-"
        default_mark = _c(" ★domyślny", "yellow") if spec.id == default_provider else ""
        pid = _c(f"{spec.id:<12}", "cyan", "bold")
        print(f"  {idx:<3} {pid} {spec.kind:<13} {token_state:<17} {clients}{default_mark}")
        if spec.notes:
            print(_c(f"      {spec.notes}", "dim"))
        if spec.token_url:
            print(f"      token: {_c(spec.token_url, 'blue')}")
    print()


def _pick_from_list(label: str, options: list[str], current: str | None) -> str | None:
    """Numbered select-list; Enter keeps ``current``; free text allowed."""
    print(_c(f"\n{label}", "bold"))
    for idx, option in enumerate(options, start=1):
        mark = _c(" (aktualny)", "yellow") if option == current else ""
        print(f"  {idx}) {option}{mark}")
    hint = f"Enter = {current or 'bez zmian'}"
    raw = input(f"Wybór [1-{len(options)}, nazwa, {hint}]: ").strip()
    if not raw:
        return current
    if raw.isdigit() and 1 <= int(raw) <= len(options):
        return options[int(raw) - 1]
    return raw


def _pick_index(count: int) -> int | None:
    raw = input(f"Wybierz providera [1-{count}, Enter=wyjście]: ").strip()
    if not raw:
        return None
    try:
        idx = int(raw)
    except ValueError:
        print(_c("Nieprawidłowy wybór.", "red"), file=sys.stderr)
        return None
    if not 1 <= idx <= count:
        print(_c("Poza zakresem.", "red"), file=sys.stderr)
        return None
    return idx - 1


def _configure_token(spec, resolve_token, save_token) -> bool:
    """Token step; Enter keeps the existing token. Returns False to abort."""
    current = resolve_token(spec.id)
    if spec.kind == "local":
        print(_c("Provider lokalny — token niepotrzebny.", "dim"))
        return True
    if spec.token_url:
        print(f"Token do pobrania tutaj: {_c(spec.token_url, 'blue')}")
    suffix = " [Enter = zostaw obecny]" if current else ""
    token = getpass.getpass(f"Token {spec.label} ({spec.token_env}){suffix}: ").strip()
    if not token:
        if current:
            print(_c("Token bez zmian.", "dim"))
            return True
        print(_c("Pusty token — nic nie zapisano.", "red"), file=sys.stderr)
        return False
    save_token(spec.id, token)
    print(_c("✓ token zapisany (chmod 600)", "green"))
    return True


def tillm_setup_main(argv: list[str] | None = None) -> int:
    try:
        from tillm.providers import (
            get_default_provider,
            iter_provider_specs,
            probe_provider,
            provider_default_model,
            resolve_provider_token,
            save_provider_token,
            set_default_provider,
        )
        from tillm.registry import available_client_ids
    except ImportError as exc:
        print(f"koru tillm: tillm package unavailable: {exc}", file=sys.stderr)
        print("Install it with `pip install tillm`.", file=sys.stderr)
        return 2

    specs = list(iter_provider_specs())
    available = set(available_client_ids())
    default_provider = get_default_provider()
    _print_provider_table(specs, resolve_provider_token, available, default_provider)

    if not sys.stdin.isatty():
        print(
            "Sesja nieinteraktywna — użyj: koru tillm provider set <id> --token ... "
            "oraz koru tillm provider test <id>",
        )
        return 0

    picked = _pick_index(len(specs))
    if picked is None:
        return 0
    spec = specs[picked]

    if not _configure_token(
        spec,
        resolve_provider_token,
        lambda pid, token: save_provider_token(pid, token),
    ):
        return 2

    # Model select-list; Enter keeps the current one.
    current_model = provider_default_model(spec.id)
    if spec.models:
        model = _pick_from_list(
            f"Model dla {spec.id}:", list(spec.models), current_model
        )
    else:
        raw = input(
            f"Model dla {spec.id} [Enter = {current_model or 'domyślny providera'}]: "
        ).strip()
        model = raw or current_model
    if model and model != current_model:
        token_now = resolve_provider_token(spec.id) or ""
        save_provider_token(spec.id, token_now, model=model)
        print(_c(f"✓ model ustawiony: {model}", "green"))

    # Default provider; Enter keeps the current default.
    if spec.id != default_provider:
        answer = input(
            f"Ustawić {spec.id} jako domyślny provider dla drive? "
            f"[t/N, Enter = {default_provider or 'bez domyślnego'}]: "
        ).strip().lower()
        if answer in ("t", "tak", "y", "yes"):
            set_default_provider(spec.id)
            print(_c(f"✓ domyślny provider: {spec.id}", "green"))

    result = probe_provider(spec.id)
    mark = _c("✓", "green") if result.ok else _c("✗", "red")
    print(f"{mark} test połączenia: {result.detail}")
    if result.ok:
        primary = next(iter(spec.compatible_clients()), None)
        print(_c("\nJak używać:", "bold"))
        print(f"  tillm drive --client {primary} --provider {spec.id} --prompt '...' --execute")
        if primary:
            print(f"  export KORU_TILLM_CLIENT={primary}   # dla autonomii koru")
    return 0 if result.ok else 1
