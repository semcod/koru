# Konfiguracja LLM, klientów i providerów (koru + tillm)

> **Audience:** operatorzy koru, agenci headless (`koru autonomous up`), integracje
> if-uri (`urirun/.env`). Opisuje **globalny** wybór modelu, klienta CLI i API
> providera — bez mieszania z pluginem IDE (Cursor/Windsurf).

Powiązane: [`agent-backends-architecture.md`](./agent-backends-architecture.md),
[`ide-router.md`](./ide-router.md), [`autopilot-quickstart.md`](./autopilot-quickstart.md),
tillm [`providers.md`](../../tillm/docs/providers.md).

---

## Dwa osie decyzji

Koru rozdziela **kto wykonuje ticket** od **skąd bierze token/model**:

| Oś | Przykłady | Konfiguracja |
|----|-----------|--------------|
| **Klient (shell)** | `aider`, `claude-code`, `codex`, `opencode` | `KORU_TILLM_CLIENT`, `--ide`, `URIRUN_KORU_IDE` |
| **Provider (API)** | `openrouter`, `anthropic`, `z.ai`, `deepseek` | `TILLM_PROVIDER`, `tillm provider set`, token env |

**Plugin IDE** (`--ide cursor`, `vscode`, `jetbrains`) to trzeci tryb — używa LLM
wbudowanego w edytor, nie tillm provider overlay.

```
koru autonomous up
       │
       ├─ --ide cursor / vscode / …  →  plugin socket  →  LLM edytora
       │
       └─ --ide aider / claude-code / …  →  tillm drive  →  provider API  →  vendor CLI
```

---

## Gdzie trzymać konfigurację

Koru ładuje pliki **w tej kolejności** (pierwszy wygrywa dla danego klucza;
istniejące zmienne w shellu **nigdy** nie są nadpisywane):

1. `<project>/.env`
2. `<project>/.env.local`
3. `<project>/urirun/.env` — kanoniczne źródło w monorepo **if-uri**

Dodatkowo:

| Miejsce | Zakres |
|---------|--------|
| `~/.config/tillm/providers.json` | Tokeny providerów (chmod 600); `TILLM_CONFIG_DIR` w testach |
| `koru.yaml` → `planning_assistant` | Planowanie strategii (nie headless drive) |
| `.planfile/.koru/shell-env.sh` | Lane isolation po `koru --init-agent-lane` |

Na starcie `koru autonomous up` wywoływane jest `load_dotenv(project)` — nie
wystarczy samo `cd` do katalogu bez `--project`.

---

## Headless drive — zmienne środowiskowe

Używane przez `koru autonomous` gdy `--ide` wskazuje klienta tillm (warstwa C
w [`agent-backends-architecture.md`](./agent-backends-architecture.md)).

| Zmienna | Opis | Przykład |
|---------|------|----------|
| `KORU_TILLM_CLIENT` | Kanoniczny klient tillm | `aider` |
| `URIRUN_KORU_IDE` | Alias if-uri (ten sam sens) | `aider` |
| `TILLM_PROVIDER` | Pojedynczy provider API (gdy brak `TILLM_PROVIDER_ORDER`) | `openrouter` |
| `TILLM_PROVIDER_ORDER` | Łańcuch fallback przy wyczerpaniu limitu (429/402) | `subscription,z.ai,openrouter` |
| `KORU_TILLM_MODEL` | Model przekazywany do CLI | `openrouter/deepseek/deepseek-v4-pro` |
| `KORU_TILLM_EXECUTE_PROFILE` | Profil headless tillm | puste → `default`; `automation` tylko dla claude-code/codex |
| `KORU_TILLM_TIMEOUT_SECONDS` | Timeout subprocessu | `600` |
| `KORU_AUTOPILOT_BACKEND` | `tillm_shell` dla headless | `tillm_shell` |
| `KORU_AUTO_SHELL_CLIENT` | `0` = wyłącz autodetekcję PATH przy `--ide auto` | `0` |

**Precedencja wyboru klienta** (`configure_loop_state`):

1. `--ide <client>` (jawny argument)
2. `KORU_TILLM_CLIENT` / `URIRUN_KORU_IDE` (z `.env`)
3. Autodetekcja: pierwszy launchable klient na PATH (często `claude-code`) —
   **ustaw jawny klient**, jeśli nie chcesz Claude subskrypcji

**Precedencja providera** (tillm):

`--provider` > `TILLM_PROVIDER_ORDER` (łańcuch z automatycznym fallbackiem przy 429/402) > `TILLM_PROVIDER` > domyślny z `tillm provider set`

### Łańcuch fallback (subscription → z.ai → OpenRouter)

```bash
# urirun/.env
TILLM_PROVIDER_ORDER=subscription,z.ai,openrouter
KORU_TILLM_CLIENT=claude-code
KORU_TILLM_MODEL=openrouter/deepseek/deepseek-v4-pro   # używany na ostatnim kroku
```

Kolejność prób przy `drive` / `koru autonomous`:

1. **`subscription`** — natywna subskrypcja Claude (`claude-code` bez overlay tillm; wymaga `claude login`)
2. **`z.ai`** — GLM przez endpoint Anthropic/OpenAI (token `ZAI_API_KEY`)
3. **`openrouter`** — gdy poprzednie zwrócą 429/402; dla `claude-code` tillm **przełącza klienta na `aider`**

Dla klienta `aider` krok `subscription` jest pomijany (brak subskrypcji); łańcuch to `z.ai` → `openrouter`.

Wyłącz łańcuch i wróć do jednego providera: usuń `TILLM_PROVIDER_ORDER` i ustaw `TILLM_PROVIDER=openrouter`.

---

## Gotowe profile

### OpenRouter + aider (zalecane dla if-uri / headless CI)

```bash
# urirun/.env lub <project>/.env
OPENROUTER_API_KEY=sk-or-...
TILLM_PROVIDER=openrouter
KORU_TILLM_CLIENT=aider
KORU_TILLM_MODEL=openrouter/deepseek/deepseek-v4-pro
KORU_TILLM_EXECUTE_PROFILE=
KORU_AUTOPILOT_BACKEND=tillm_shell
```

```bash
koru --init-agent-lane --agent-lane aider --project .
koru autonomous up --project . --agent-lane aider --ide aider
```

### Claude Code — natywna subskrypcja Anthropic

```bash
# Login w ~/.claude lub ANTHROPIC_API_KEY
export KORU_TILLM_CLIENT=claude-code
export KORU_TILLM_MODEL=claude-sonnet-4-...
# TILLM_PROVIDER=anthropic  # opcjonalnie
koru autonomous up --project . --ide claude-code
```

Uwaga: subskrypcja claude.ai ma limity tygodniowe; przy 429 użyj providera API
(OpenRouter, z.ai) zamiast bezpośredniej subskrypcji.

### Claude Code przez z.ai (GLM)

```bash
tillm provider set z.ai --token "$ZAI_API_KEY" --model glm-4.7
export TILLM_PROVIDER=z.ai
export KORU_TILLM_CLIENT=claude-code
koru autonomous up --project . --ide claude-code
```

### Synchronizacja konfiguracji między narzędziami (`tillm provider sync`)

Store tillm (`~/.config/tillm/providers.json`) jest jedynym źródłem prawdy o
tokenie providera. `sync` uzgadnia z nim pozostałe konfiguracje na maszynie —
na obu poziomach:

- **terminal**: Claude Code (`~/.claude/settings.json`), Codex
  (`~/.codex/config.toml`), opencode (`~/.config/opencode/opencode.json`),
- **gui**: JetBrains AI Assistant (OpenAI-like) i Qoder — tylko detekcja i
  raport (klucz siedzi w keychainie IDE; wpisujesz go raz w ustawieniach IDE
  albo dialog wyklikuje gillm).

```bash
tillm provider sync z.ai                    # dry-run: plan na oba poziomy
tillm provider sync z.ai --level terminal   # tylko narzędzia shellowe
tillm provider sync z.ai --apply            # import brakującego tokenu + zapisy
```

Kierunki: gdy store nie ma tokenu, a któraś powierzchnia ma → **import** do
store; gdy store ma token → **eksport** do zapisywalnych powierzchni, którym
go brakuje lub mają nieaktualny. Tokeny nigdy nie trafiają do wyjścia komendy.

Uwaga: eksport do `~/.claude/settings.json` przestawia **każde** ręcznie
odpalone `claude` na danego providera (subskrypcja Anthropic przestaje być
domyślna) — dry-run ostrzega o tym w planie. Klienci odpalani przez
`tillm drive`/`koru -a` nie potrzebują syncu — dostają env overlay przy starcie.

`tillm provider sync` **bez argumentu** drukuje macierz całej maszyny: każdy
zarejestrowany provider (z.ai, MiniMax, Moonshot/Kimi, DeepSeek, xAI, Mistral,
Groq, Qwen, …) × każda powierzchnia, z linkiem `token_url` tam, gdzie brakuje
klucza — to jest punkt startowy automatu integracyjnego.

### Kolejka priorytetów providerów (`tillm provider order`)

Kolejność fallbacku można utrwalić w store (bez grzebania w env):

```bash
tillm provider order                          # pokaż aktualną kolejkę
tillm provider order subscription z.ai minimax openrouter   # ustaw
tillm provider order --clear                  # usuń
```

Precedencja przy drive: `--provider` (bez fallbacku) → env
`TILLM_PROVIDER_ORDER` → **kolejka ze store** → pojedynczy
`TILLM_PROVIDER`/domyślny. Providerzy bez tokenu są pomijani automatycznie.

### Autonomiczna zmiana providera a tickety

Gdy pętla autonomiczna koru trafi na wyczerpany limit (429/402), przechodzi na
następnego providera z kolejki. Taka zmiana jest raportowana:

- na żywo w logu pętli (`shell-drive: [KORU-SHELL-DRIVE] provider-switch: …`),
- **w notce ticketa**, który był wtedy prowadzony — wpis
  `provider-switch: z.ai → minimax — 'z.ai' unavailable/exhausted (limit?),
  koru autonomously drove this ticket with 'minimax'` plus podpowiedź, jak
  zmienić kolejkę (`tillm provider order …`).

Każda notka drive'a zawiera też `provider=<id>`, więc po fakcie widać, który
provider wykonał pracę nad ticketem.

### OpenAI Codex

```bash
export TILLM_PROVIDER=openai
export KORU_TILLM_CLIENT=codex
export OPENAI_API_KEY=sk-...
koru autonomous up --project . --ide codex
```

### Plugin IDE (bez tillm)

```bash
koru autonomous up --project . --agent-lane cursor --ide cursor
# Model = LLM Cursor; OpenRouter w .env nie steruje chatem IDE
```

---

## Inne role LLM w koru (osobne od headless drive)

Zmiana `KORU_TILLM_MODEL` **nie** przełącza wszystkich wywołań LLM w koru:

| Rola | Zmienne | Zadanie |
|------|---------|---------|
| Headless wykonawca | `KORU_TILLM_MODEL` | Edycja kodu przez tillm CLI |
| Planowanie | `KORU_PLANNING_LLM`, `KORU_PLANNING_LLM_MODEL` | Priorytety, tuning strategii |
| NXDO discovery | `KORU_NXDO_MODEL` | Auto-tickety z code2llm |
| Refleksja po cyklu | `KORU_LLM_REFLECT` | Podsumowania (nxdo/llx) |
| pfix | `LLM_MODEL`, `OPENROUTER_API_KEY` | Self-healing Python |
| Kolejka HTTP | `KORU_LLM_ENDPOINT`, model w ticket JSON | OpenRouter/OpenAI per ticket |
| Wizja | `KORU_VISION_*`, modele w `.env` projektu | Screenshot / grounding |

`koru.yaml` → `planning_assistant.provider_order` definiuje fallback planowania
(`openrouter` → `ide_llm`).

---

## Interaktywna konfiguracja (tillm store)

```bash
koru tillm                              # wizard: klient + provider + token + probe
tillm providers                         # lista providerów + status tokenów
tillm clients                           # lista klientów + profile execute
tillm provider set openrouter           # zapis tokena (getpass), probe
tillm provider test openrouter
tillm provider probe openrouter
```

Dry-run bez pełnego autonomous:

```bash
tillm drive --client aider --provider openrouter \
  --model openrouter/deepseek/deepseek-v4-pro \
  --prompt 'Reply with exactly: ok' --dry-run
```

---

## Weryfikacja po zmianie `.env`

```bash
cd /path/to/project
python3 -c "
from pathlib import Path
from koru.dotenv_loader import load_dotenv
import os
load_dotenv(Path('.'))
print('client:', os.getenv('KORU_TILLM_CLIENT'))
print('provider:', os.getenv('TILLM_PROVIDER'))
print('model:', os.getenv('KORU_TILLM_MODEL'))
print('openrouter:', bool(os.getenv('OPENROUTER_API_KEY')))
"
```

Oczekiwany komunikat przy starcie autonomous (gdy env wskazuje aider):

```text
[koru] using shell client 'aider' from KORU_TILLM_CLIENT/URIRUN_KORU_IDE.
```

---

## Typowe błędy

| Objaw | Przyczyna | Naprawa |
|-------|-----------|---------|
| `429 Weekly/Monthly Limit Exhausted` (claude) | Headless szedł w `claude-code` + subskrypcję | `KORU_TILLM_CLIENT=aider`, `TILLM_PROVIDER=openrouter` |
| `unsupported execute profile 'automation'` (aider) | Wymuszony profil automation | `KORU_TILLM_EXECUTE_PROFILE=` (puste) lub usuń z env |
| `openrouter: no` w brief mimo klucza w `urirun/.env` | Koru nie ładował `urirun/.env` | Zaktualizuj koru (≥ patch z `urirun/.env` w dotenv); `koru autonomous up --project .` |
| `402` / `requires more credits` (OpenRouter) | Tygodniowy limit klucza OpenRouter wyczerpany | Podnieś limit na openrouter.ai → Keys, albo `TILLM_PROVIDER=z.ai` / inny provider z tokenem |
| Autodetekcja wybiera `claude-code` | `--ide auto`, brak edytora, claude pierwszy na PATH | Jawny `--ide aider` lub `KORU_TILLM_CLIENT` |
| Provider bez tokena | Brak env i brak wpisu w tillm store | `tillm provider set <id>` lub export `*_API_KEY` |

---

## if-uri — mapowanie ról w `urirun/.env`

W ekosystemie if-uri pełna matryca modeli jest w `urirun/.env.example`:

- `LLM_MODEL_DEVELOPER` — ten sam model co agent:// / aider
- `LLM_MODEL_PLANNER` / `KORU_PLANNING_LLM_MODEL` — planowanie
- `LLM_MODEL_EXECUTOR`, `VALIDATOR`, `TEACHER` — triple-LLM KVM/Signal
- `URIRUN_LLM_API_BASE` — opcjonalny proxy (`https://llm.urirun.com/api/v1`)

Po zmianie: zrestartuj `koru autonomous` i dashboard `/work` (8797).

---

## Powiązane komendy

```bash
koru ide-router --format json          # aktywny lane + IDE
koru agent --env-exports --agent-lane aider   # exporty lane
koru tillm providers
koru autonomous up --help              # --ide, --agent-lane, --llm-model
```
