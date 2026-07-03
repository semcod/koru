"""Interactive setup for shell LLM tools and API providers (``koru tillm``).

Full provider list comes from tillm's registry (most popular / newest first).
Flow: pick a provider, paste a token (link to the token page is printed;
Enter keeps the existing token), pick a model from a select-list (Enter keeps
the current one), optionally make the provider the default for every drive.

Language: English by default; ``--lang pl|de|en`` chooses and persists,
``TILLM_LANG`` and the system locale are honoured (see tillm.i18n).
All provider logic lives in tillm; this is only the koru-side UI.
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


def _print_provider_table(_, specs, resolve_token, available_clients, default_provider):
    print()
    print(_c(_("picker.title"), "bold"))
    print()
    header = (
        f"  {'#':<3} {_('picker.col.provider'):<12} {_('picker.col.kind'):<13} "
        f"{_('picker.col.token'):<9} {_('picker.col.clients')}"
    )
    print(_c(header, "dim"))
    print(_c("  " + "-" * (len(header) - 2), "dim"))
    for idx, spec in enumerate(specs, start=1):
        has_token = bool(resolve_token(spec.id)) or spec.kind == "local"
        token_state = (
            _c(_("picker.token.set"), "green")
            if has_token
            else _c(_("picker.token.missing"), "red")
        )
        clients = ", ".join(
            (cid + (_c("✓", "green") if cid in available_clients else ""))
            for cid in spec.compatible_clients()
        ) or "-"
        default_mark = (
            _c(_("picker.default_mark"), "yellow") if spec.id == default_provider else ""
        )
        pid = _c(f"{spec.id:<12}", "cyan", "bold")
        print(f"  {idx:<3} {pid} {spec.kind:<13} {token_state:<18} {clients}{default_mark}")
        if spec.notes:
            print(_c(f"      {spec.notes}", "dim"))
        if spec.token_url:
            print(f"      {_('picker.token_page')}: {_c(spec.token_url, 'blue')}")
    print()


def _pick_from_list(_, label: str, options: list[str], current: str | None) -> str | None:
    """Numbered select-list; Enter keeps ``current``; free text allowed."""
    print(_c(f"\n{label}", "bold"))
    for idx, option in enumerate(options, start=1):
        mark = _c(_("model.current"), "yellow") if option == current else ""
        print(f"  {idx}) {option}{mark}")
    raw = input(
        _("model.choose", count=len(options), current=current or _("keep.unchanged"))
    ).strip()
    if not raw:
        return current
    if raw.isdigit() and 1 <= int(raw) <= len(options):
        return options[int(raw) - 1]
    return raw


def _pick_index(_, count: int) -> int | None:
    raw = input(_("picker.choose", count=count)).strip()
    if not raw:
        return None
    try:
        idx = int(raw)
    except ValueError:
        print(_c(_("picker.invalid"), "red"), file=sys.stderr)
        return None
    if not 1 <= idx <= count:
        print(_c(_("picker.out_of_range"), "red"), file=sys.stderr)
        return None
    return idx - 1


def _configure_token(_, spec, resolve_token, save_token) -> bool:
    """Token step; Enter keeps the existing token. Returns False to abort."""
    current = resolve_token(spec.id)
    if spec.kind == "local":
        print(_c(_("token.local"), "dim"))
        return True
    if spec.token_url:
        print(_("token.get_here", url=_c(spec.token_url, "blue")))
    keep = _("token.keep_suffix") if current else ""
    token = getpass.getpass(
        _("token.prompt", label=spec.label, env=spec.token_env, keep=keep)
    ).strip()
    if not token:
        if current:
            print(_c(_("token.unchanged"), "dim"))
            return True
        print(_c(_("token.empty"), "red"), file=sys.stderr)
        return False
    save_token(spec.id, token)
    print(_c(_("token.saved"), "green"))
    return True


def _extract_lang(argv: list[str]) -> tuple[str | None, list[str]]:
    """Pop --lang/--lang=<code> from argv."""
    lang: str | None = None
    rest: list[str] = []
    skip = False
    for idx, part in enumerate(argv):
        if skip:
            skip = False
            continue
        if part == "--lang" and idx + 1 < len(argv):
            lang, skip = argv[idx + 1], True
        elif part.startswith("--lang="):
            lang = part.split("=", 1)[1]
        else:
            rest.append(part)
    return lang, rest


def tillm_setup_main(argv: list[str] | None = None) -> int:
    try:
        from tillm.i18n import _, save_language, set_language, yes_answers
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

    lang, _rest = _extract_lang(list(argv or []))
    if lang:
        chosen = set_language(lang)
        saved = save_language(lang)
        if saved:
            print(_c(_("lang.set", lang=chosen), "green"))

    specs = list(iter_provider_specs())
    available = set(available_client_ids())
    default_provider = get_default_provider()
    _print_provider_table(_, specs, resolve_provider_token, available, default_provider)

    if not sys.stdin.isatty():
        print(_("noninteractive.hint"))
        return 0

    picked = _pick_index(_, len(specs))
    if picked is None:
        return 0
    spec = specs[picked]

    if not _configure_token(
        _, spec, resolve_provider_token, lambda pid, token: save_provider_token(pid, token)
    ):
        return 2

    # Model select-list; Enter keeps the current one.
    current_model = provider_default_model(spec.id)
    if spec.models:
        model = _pick_from_list(_, _("model.label", id=spec.id), list(spec.models), current_model)
    else:
        raw = input(
            _("model.freeform", id=spec.id, current=current_model or _("model.provider_default"))
        ).strip()
        model = raw or current_model
    if model and model != current_model:
        token_now = resolve_provider_token(spec.id) or ""
        save_provider_token(spec.id, token_now, model=model)
        print(_c(_("model.set", model=model), "green"))

    # Default provider; Enter keeps the current default.
    if spec.id != default_provider:
        answer = input(
            _("default.question", id=spec.id, current=default_provider or _("default.none"))
        ).strip().lower()
        if answer in yes_answers():
            set_default_provider(spec.id)
            print(_c(_("default.set", id=spec.id), "green"))

    result = probe_provider(spec.id)
    mark = _c("✓", "green") if result.ok else _c("✗", "red")
    print(f"{mark} {_('probe.label', detail=result.detail)}")
    if result.ok:
        primary = next(iter(spec.compatible_clients()), None)
        print(_c(f"\n{_('usage.title')}", "bold"))
        print(f"  tillm drive --client {primary} --provider {spec.id} --prompt '...' --execute")
        if primary:
            print(f"  export KORU_TILLM_CLIENT={primary}   {_('usage.autonomy')}")
    return 0 if result.ok else 1
