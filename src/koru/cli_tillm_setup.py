"""Interactive setup for shell LLM tools and API providers (``koru tillm``).

Shows the tools/providers tillm supports (claude-code via Anthropic or z.ai,
aider via OpenRouter/z.ai, …), lets the operator pick one, paste a token, and
verifies it live. All provider logic lives in tillm (its responsibility);
this module is only the koru-side picker UI.
"""

from __future__ import annotations

import getpass
import sys


def _print_provider_table(specs, resolve_token, available_clients: set[str]) -> None:
    print("\nDostępne narzędzia / providerzy (tillm):\n")
    header = f"  {'#':<3} {'provider':<12} {'typ':<13} {'token':<8} klienci (✓ = binarka w PATH)"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for idx, spec in enumerate(specs, start=1):
        token_state = "✓ jest" if resolve_token(spec.id) else "✗ brak"
        clients = ", ".join(
            f"{cid}{'✓' if cid in available_clients else ''}"
            for cid in spec.compatible_clients()
        ) or "-"
        print(f"  {idx:<3} {spec.id:<12} {spec.kind:<13} {token_state:<8} {clients}")
        if spec.notes:
            print(f"      {spec.notes}")
    print()


def _pick_index(count: int) -> int | None:
    raw = input(f"Wybierz providera [1-{count}, Enter=wyjście]: ").strip()
    if not raw:
        return None
    try:
        idx = int(raw)
    except ValueError:
        print("Nieprawidłowy wybór.", file=sys.stderr)
        return None
    if not 1 <= idx <= count:
        print("Poza zakresem.", file=sys.stderr)
        return None
    return idx - 1


def tillm_setup_main(argv: list[str] | None = None) -> int:
    try:
        from tillm.providers import (
            iter_provider_specs,
            probe_provider,
            resolve_provider_token,
            save_provider_token,
        )
        from tillm.registry import available_client_ids
    except ImportError as exc:
        print(f"koru tillm: tillm package unavailable: {exc}", file=sys.stderr)
        print("Install it with `pip install tillm`.", file=sys.stderr)
        return 2

    specs = list(iter_provider_specs())
    available = set(available_client_ids())
    _print_provider_table(specs, resolve_provider_token, available)

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

    current = resolve_provider_token(spec.id)
    if current:
        print(f"Token dla {spec.id} już jest ustawiony ({spec.token_env} lub magazyn).")
        answer = input("Nadpisać? [t/N]: ").strip().lower()
        if answer not in ("t", "tak", "y", "yes"):
            result = probe_provider(spec.id)
            print(("✓" if result.ok else "✗") + f" test: {result.detail}")
            return 0 if result.ok else 1

    token = getpass.getpass(f"Token {spec.label} ({spec.token_env}): ").strip()
    if not token:
        print("Pusty token — nic nie zapisano.", file=sys.stderr)
        return 2

    model = input("Domyślny model (Enter = domyślny providera): ").strip() or None
    path = save_provider_token(spec.id, token, model=model)
    print(f"✓ zapisano token w {path} (chmod 600)")

    result = probe_provider(spec.id)
    print(("✓" if result.ok else "✗") + f" test połączenia: {result.detail}")
    if result.ok:
        primary = next(iter(spec.compatible_clients()), None)
        print("\nJak używać:")
        print(f"  tillm drive --client {primary} --provider {spec.id} --prompt '...' --execute")
        print(f"  # lub w autonomii koru: export TILLM_PROVIDER={spec.id}")
        if primary:
            print(f"  export KORU_TILLM_CLIENT={primary}")
    return 0 if result.ok else 1
