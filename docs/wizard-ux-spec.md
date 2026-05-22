# koru wizard — UX spec for non-technical users

Status: **draft**, owner: Tom Sapletta, created: 2026-05-22.

This is the design contract for the next round of `koru wizard` improvements.
Six features in scope, ordered by user-visible impact:

1. Bilingual side-by-side labels (foundation — affects all other features)
2. Per-option help dictionary `[?]`
3. `--quick` zero-prompt mode
4. Post-creation guidance (next-3-steps panel)
5. Strategy templates marketplace (`--template`, `--strategies URL`)
6. `--gui` browser front-end

The IDE-install-proposal feature is **out of scope** for this iteration (kept
in backlog as `wizard-ide-install-spec.md`).

---

## 0. Design constraints (cross-cutting)

* Backwards compatibility: existing `koru wizard` calls keep working with no
  flag changes. New flags are additive.
* `strategies.json` schema version stays **1**; new fields are optional and
  default-tolerant (older trees still load).
* No new required dependencies. `--gui` adds an optional dep group
  `wizard-gui` (FastAPI + uvicorn already used elsewhere in koru, so re-use).
* The decision tree is the single source of truth. CLI, GUI, and `--quick`
  all read the same `StrategyTree`.
* Localisation: every user-facing string must accept `{pl, en}` dict form
  with the existing `_pick_localized` fallback.

---

## 1. Bilingual side-by-side labels

### Goal
Remove the *first* friction point: today users may not know whether they want
PL or EN, and the choice is sticky for the whole session. Show both languages
in one label.

### UX
Before:
```
[1] Architektura projektu
```
After (when bilingual mode active):
```
[1] Architektura projektu  ·  Project architecture
```

### Schema / data
No schema change. The renderer concatenates `pl` + ` · ` + `en` when both
exist and `--bilingual` (or `KORU_WIZARD_BILINGUAL=1`) is set, **or** when
`strategies.json` declares `"bilingual_default": true`.

### CLI
* `--bilingual` / `--no-bilingual` flag, defaults to **off** for now.
* Env override: `KORU_WIZARD_BILINGUAL=1`.
* `--language=pl,en` (comma-separated) becomes the explicit form; CLI sniffs
  the locale (`LANG`) to auto-enable when both `pl_PL` and English texts are
  present.

### Implementation
* New `tree._pick_localized_multi(value, langs: list[str]) -> str` that joins
  with ` · ` and dedupes when both translations are identical.
* `load_tree(..., language=...)` accepts `str | list[str]`.
* `cli.py` parses comma-separated `--language`.

### Tests
* `test_tree_pick_localized_multi_joins_with_separator`
* `test_tree_load_supports_language_list`
* `test_cli_bilingual_flag_renders_both_languages` (uses ScriptedPrompter +
  captures `seen_prompts`).

### Acceptance
* Existing single-language tests still pass.
* `koru wizard --bilingual --detect-only` is a no-op for IDE list (only
  affects tree labels).
* Token ` · ` (U+00B7) is configurable via `KORU_WIZARD_BILINGUAL_SEPARATOR`.

### Scope
~80 lines, 1 commit.

---

## 2. Per-option help dictionary `[?]`

### Goal
Non-tech users see "CQRS+ES" or "Hexagonal architecture" and bounce. Add a
1-2 sentence explanation per option, available on-demand without leaving the
prompt.

### UX
```
Co Cię najbardziej interesuje?
  [1] Architektura projektu       [?]
  [2] Frontend / UI / UX           [?]
  …
  [?] = wyjaśnij wszystkie opcje
> ?2
   Frontend / UI / UX
   ──────────────────
   Wygląd i interakcje aplikacji widoczne dla użytkownika końcowego.
   Obejmuje design system, accessibility, performance renderingu.

> 2     ← user then picks
```

### Schema
`strategies.json` gains optional `help` per option/ticket:
```json
{"id": "cqrs_es", "label": {"pl": "..."}, "ticket": "tpl_cqrs_es",
 "help": {"pl": "...", "en": "..."}}
```
Backwards compatible: missing `help` shows `(brak opisu / no description)`.

### CLI grammar
* User types `?N` to see help for option N, prompt re-displays.
* `?` alone lists help for all options.
* `?q` quits help and returns to prompt.

### Implementation
* `TreeOption` gains `help: str` (already localised at load time).
* `StdinPrompter.ask_choice` parses `?…` prefix before regular answers.
* GUI mode (feature 6) renders help as expandable info-icon next to each
  option.

### Tests
* `test_tree_option_help_loaded_when_present`
* `test_stdin_prompter_question_mark_shows_help` (uses io.StringIO with
  scripted answers `?1\n?\n1\n`).
* `test_walk_help_does_not_advance_path`.

### Acceptance
* Backwards-compatible: existing strategies.json without `help` loads fine.
* Pressing `?` never ends the wizard.
* Default `strategies.json` ships with `help` for ALL 26 ticket templates.

### Scope
~150 lines, 1 commit. Includes content writing for help strings.

---

## 3. `--quick` zero-prompt mode

### Goal
Single-keystroke first-time success. User installs koru, runs
`koru wizard --quick`, gets a sensible first ticket without ANY prompts.

### Default strategy chosen
`quality → cc_refactor` — every project benefits, requires no domain
knowledge, produces actionable backlog.

Override in `strategies.json`:
```json
"quick_default": {
  "path": ["quality", "cc_refactor"],
  "description_pl": "Domyślny pierwszy ticket: redukcja CC w 5 hotspotach.",
  "description_en": "Default first ticket: reduce CC in 5 hotspots."
}
```

### UX
```
$ koru wizard --quick
✓ koru wizard --quick
  Project  : /home/tom/myproj  (auto-picked: shell cwd)
  Strategy : quality → cc_refactor   (default for --quick)
  Ticket   : PLF-001 — Quality: redukcja CC w hotspotach
  Next     : run `koru` to see the LLM brief.

(re-run with `koru wizard` to pick a different strategy interactively)
```

### CLI
* `--quick` implies: skip IDE prompt, skip project prompt (use cwd or
  `--project`), follow `quick_default.path`, create ticket, print summary.
* `--quick --strategy <path.dotted>` overrides default (e.g. `--quick
  --strategy architecture.cqrs_es`).

### Implementation
* `cli.run_wizard(quick=True, strategy_path=None)` follows the JSON-encoded
  path without invoking the prompter.
* Walks tree node-by-node; raises clear error when path is invalid.

### Tests
* `test_quick_mode_creates_ticket_without_prompts`
* `test_quick_mode_with_custom_strategy_path`
* `test_quick_mode_falls_back_when_path_missing`.

### Acceptance
* Zero stdin reads in `--quick` mode (verifiable by feeding `StringIO("")`).
* Exits 0 even when project has no `.planfile` yet (creates it).

### Scope
~120 lines, 1 commit.

---

## 4. Post-creation guidance

### Goal
After ticket creation, user knows EXACTLY which command to run next. Today's
output ends at "Created PLF-001"; user might think they're done.

### UX
```
✓ koru wizard finished
  IDE      : Cursor
  Project  : /home/tom/myproj
  Strategy : quality → cc_refactor
  Ticket   : PLF-001 — Quality: redukcja CC w hotspotach

Co teraz / What's next:
  1. `koru` — wyświetli brief LLM do wklejenia w Cursor/Cascade
  2. Otwórz Cursor i napisz: "Pracuj nad ticketem PLF-001"
  3. `koru --queue --loop` — agent sam przepracuje kolejkę

Edytuj strategie w: /home/tom/.config/koru/strategies.json
(skopiuj `koru wizard --print-strategies > my.json` żeby zacząć)
```

### Schema
`strategies.json.tickets[*].next_steps`: localised list, optional. Falls
back to a global default in `strategies.json.defaults.next_steps`.

### Implementation
* `TicketTemplate.next_steps: tuple[str, ...]`
* `_emit_human` renders the panel.
* GUI mode shows it as a card.

### Tests
* `test_ticket_template_loads_next_steps`
* `test_post_creation_panel_contains_steps`
* `test_post_creation_falls_back_to_default_steps`.

### Acceptance
* Steps must be **commands or single sentences**, not paragraphs.
* If `--no-create`, panel still prints "would create" preview.

### Scope
~100 lines + content writing, 1 commit.

---

## 5. Strategy templates marketplace

### Goal
Curated starting points for common project shapes (web app, ML research,
CLI tool, library). Power users + non-tech users both benefit.

### UX
```
$ koru wizard --list-templates
Built-in templates:
  default            — General-purpose decision tree (7 root branches)
  web-app            — Frontend + Backend + DevOps for SPAs
  ml-research        — Experiments, reproducibility, data quality
  cli-tool           — Distribution, packaging, semver, docs
  library            — API stability, type stubs, examples, CI

$ koru wizard --template web-app
[wizard walks the web-app tree]

$ koru wizard --strategies https://raw.githubusercontent.com/.../tree.json
[fetches over HTTPS, caches in ~/.cache/koru/wizard/]
```

### File layout
* `src/koru/wizard/templates/default.json` — symlink/copy of current strategies.json
* `src/koru/wizard/templates/web-app.json`
* `src/koru/wizard/templates/ml-research.json`
* `src/koru/wizard/templates/cli-tool.json`
* `src/koru/wizard/templates/library.json`
* `src/koru/wizard/templates/registry.json` — maps `name -> path + description`

### CLI
* `--template <name>` — load from packaged templates.
* `--list-templates` — print registry.
* `--strategies <path|url>` — already supported, extend to accept URLs
  (https only) with 1MB max size, 5s timeout, SHA-256 cache key.

### Implementation
* `templates.py` module: `list_templates() -> list[TemplateInfo]`,
  `resolve_template(name_or_url) -> Path`.
* URL fetch behind small abstraction so tests can stub.

### Tests
* `test_list_templates_returns_packaged_set`
* `test_resolve_template_by_name`
* `test_resolve_template_rejects_non_https_url`
* `test_resolve_template_caches_remote` (mock requests).

### Acceptance
* `--template` and `--strategies` are mutually exclusive (parse-time error).
* HTTPS fetch is opt-in (allow-list to known hosts? or always require
  `--allow-remote` flag? **decision: require `--allow-remote` for security**).

### Scope
~250 lines + 4 template JSONs, 1 commit. Content authoring is the biggest
chunk.

---

## 6. `--gui` browser front-end

### Goal
Zero-terminal experience. User runs `koru wizard --gui`, browser opens at
`http://localhost:8765/wizard`, they click through, ticket gets created.

### UX flow
1. CLI starts FastAPI + uvicorn on 127.0.0.1 free port.
2. Opens `webbrowser.open()` automatically (skip with `--no-browser`).
3. Single-page app:
   - **Step 1**: IDE picker (cards with logos, "running" badge).
   - **Step 2**: Project picker (cards with path + source label).
   - **Step 3**: Strategy walker (one node per page, large buttons,
     `[?]` becomes a tooltip / expandable card).
   - **Step 4**: Confirmation + post-creation panel (feature 4).
4. After ticket creation, server shows "OK" and shuts down on next request
   (`/done` endpoint).

### Tech choices
* FastAPI (already in `optional-dependencies.api`).
* Jinja2 templates (single file).
* No JS framework — vanilla JS for `fetch` calls + form switching.
* Tailwind via CDN (offline fallback: bundled minimal CSS).

### File layout
* `src/koru/wizard/gui/app.py` — FastAPI app factory.
* `src/koru/wizard/gui/templates/wizard.html` — single template.
* `src/koru/wizard/gui/static/wizard.js` + `wizard.css`.

### State management
* Server keeps an in-memory `WizardSession` keyed by random UUID stored in a
  cookie. Single-user, localhost-only, no auth needed.
* Session expires after 30 min idle.

### CLI
* `--gui` — start GUI server, open browser.
* `--gui --port 0` — random port (default).
* `--gui --no-browser` — print URL only.
* `--gui --bind 127.0.0.1` — non-configurable for security (localhost only).

### Security
* Bind 127.0.0.1 only. **Refuse 0.0.0.0** even with explicit override.
* CSRF token on all POST forms.
* No file upload, no shell exec endpoints, no escape from project path.

### Tests
* `test_gui_app_factory_serves_step1`
* `test_gui_app_walks_tree_via_post`
* `test_gui_app_creates_ticket_at_final_step`
* Use `httpx.AsyncClient` against the FastAPI app — no real network.

### Acceptance
* `koru wizard --gui --no-browser` prints URL within 2s on cold start.
* Closing the browser tab doesn't leave a zombie server (auto-shutdown on
  `/done` or 30-min idle timeout).
* Works offline (no CDN required for core flow).

### Scope
~600 lines (FastAPI app + HTML + CSS + JS), 1 commit. The biggest item in
the spec — likely best **split into a follow-up branch** after features 1-5
ship.

---

## Cross-feature ordering / dependencies

```
   1. bilingual ─┐
                 ├──► 4. post-create panel (uses bilingual)
   2. help [?] ─┤        │
                 │        ▼
                 ├──► 6. GUI (consumes 1, 2, 3, 4)
   3. --quick ──┤        ▲
                 │        │
   5. templates ┘────────┘
```

Recommended order:
1. Bilingual (foundation)
2. Help dictionary (~150 lines, immediately useful)
3. `--quick` (~120 lines, zero-friction onboarding)
4. Post-creation panel (~100 lines, completes happy path)
5. Templates (~250 lines, power feature)
6. GUI (~600 lines, separate branch — `feature/wizard-gui`)

Each step is independently shippable and tested.

---

## Open questions

* Do we want **analytics** (anonymous, local-only) of which paths users
  pick? Useful for tuning the default tree, but adds privacy surface.
  Recommendation: defer to a later spec.
* Should `koru auto` automatically launch `koru wizard --gui` on
  first-run? Recommendation: only if `--gui` ships and stdin is TTY +
  `DISPLAY` is set; otherwise keep current text hint.
* `--template` over HTTPS — should we sign templates? Recommendation:
  v1 = `--allow-remote` flag + 1MB cap + display SHA-256. v2 = signature
  if community demand appears.

---

## Definition of done (per feature)

* Code + tests in same commit; coverage ≥ 90% for new modules.
* `ruff check src/koru/wizard tests/test_wizard_*.py` passes.
* `koru wizard --detect-only --format json` schema stays backwards-compat.
* README.md "Quick start" section updated.
* CHANGELOG.md entry.
* No new required dependencies (optional groups OK).
