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
from types import SimpleNamespace

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


def _load_tillm():
    """Lazily import tillm; return a bundle of its helpers, or None if missing."""
    try:
        from tillm.i18n import _, save_language, set_language, yes_answers
        from tillm.providers import (
            diagnose_provider,
            get_default_provider,
            iter_provider_specs,
            list_provider_models,
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
        return None
    return SimpleNamespace(
        _=_,
        save_language=save_language,
        set_language=set_language,
        yes_answers=yes_answers,
        diagnose_provider=diagnose_provider,
        get_default_provider=get_default_provider,
        iter_provider_specs=iter_provider_specs,
        list_provider_models=list_provider_models,
        probe_provider=probe_provider,
        provider_default_model=provider_default_model,
        resolve_provider_token=resolve_provider_token,
        save_provider_token=save_provider_token,
        set_default_provider=set_default_provider,
        available_client_ids=available_client_ids,
    )


def _apply_lang(argv: list[str], t) -> None:
    """Honour ``--lang``: switch the active language and persist the choice."""
    lang = _extract_lang(argv)[0]
    if not lang:
        return
    chosen = t.set_language(lang)
    if t.save_language(lang):
        print(_c(t._("lang.set", lang=chosen), "green"))


def _pick_provider(t, specs):
    """Return the chosen provider spec, or None to signal an early exit (rc 0).

    Non-interactive shells (no tty) print a hint and exit; an empty or invalid
    pick also exits without changing anything.
    """
    if not sys.stdin.isatty():
        print(t._("noninteractive.hint"))
        return None
    picked = _pick_index(t._, len(specs))
    if picked is None:
        return None
    return specs[picked]


def _freeform_model(t, spec, current_model: str | None) -> str | None:
    raw = input(
        t._("model.freeform", id=spec.id, current=current_model or t._("model.provider_default"))
    ).strip()
    return raw or current_model


def _choose_model(t, spec) -> None:
    """Model select-list; Enter keeps the current one. Models come live from
    the provider API (curated fallback) so the list is never stale."""
    current_model = t.provider_default_model(spec.id)
    listing = t.list_provider_models(spec.id)
    source_note = t._("models.live") if listing.source == "live" else t._("models.curated")
    options = list(listing.models[:20])
    if current_model and current_model not in options:
        options.insert(0, current_model)
    if options:
        model = _pick_from_list(
            t._, t._("model.label", id=spec.id) + f" ({source_note})", options, current_model
        )
    else:
        model = _freeform_model(t, spec, current_model)
    if model and model != current_model:
        token_now = t.resolve_provider_token(spec.id) or ""
        t.save_provider_token(spec.id, token_now, model=model)
        print(_c(t._("model.set", model=model), "green"))


def _maybe_set_default(t, spec, default_provider) -> None:
    """Offer to make the chosen provider the default; Enter keeps the current."""
    if spec.id == default_provider:
        return
    answer = input(
        t._("default.question", id=spec.id, current=default_provider or t._("default.none"))
    ).strip().lower()
    if answer in t.yes_answers():
        t.set_default_provider(spec.id)
        print(_c(t._("default.set", id=spec.id), "green"))


def _run_diagnosis(t, spec) -> int:
    diagnosis = t.diagnose_provider(spec.id)
    print(_c(f"\n{t._('diag.title')}", "bold"))
    marks = {"ok": _c("✓", "green"), "warn": _c("⚠", "yellow"), "fail": _c("✗", "red")}
    for item in diagnosis.items:
        print(f"  {marks[item.level]} {item.message}")
        if item.fix:
            print(_c(f"     fix: {item.fix}", "dim"))
    t.probe_provider(spec.id, model=t.provider_default_model(spec.id))
    if diagnosis.ok:
        primary = next(iter(spec.compatible_clients()), None)
        print(_c(f"\n{t._('usage.title')}", "bold"))
        print(f"  tillm drive --client {primary} --provider {spec.id} --prompt '...' --execute")
        if primary:
            print(f"  export KORU_TILLM_CLIENT={primary}   {t._('usage.autonomy')}")
    return 0 if diagnosis.ok else 1


def tillm_setup_main(argv: list[str] | None = None) -> int:
    t = _load_tillm()
    if t is None:
        return 2

    _apply_lang(list(argv or []), t)

    specs = list(t.iter_provider_specs())
    available = set(t.available_client_ids())
    default_provider = t.get_default_provider()
    _print_provider_table(t._, specs, t.resolve_provider_token, available, default_provider)

    spec = _pick_provider(t, specs)
    if spec is None:
        return 0

    if not _configure_token(t._, spec, t.resolve_provider_token, t.save_provider_token):
        return 2

    _choose_model(t, spec)
    _maybe_set_default(t, spec, default_provider)
    return _run_diagnosis(t, spec)
