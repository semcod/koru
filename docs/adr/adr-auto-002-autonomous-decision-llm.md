# ADR AUTO-002 — Autonomiczna pętla decyzyjna: OpenRouter LLM + heurystyki + IDE LLM

- Status: **Phase 1-3 implemented; Phase 4 wired (reflection runtime + advisory hooks)**
- Date: 2026-05-25
- Updated: 2026-09-01
- Related: `koru.yaml` `autonomy.strategy.planning_assistant`, external
  `korullm>=0.1.0`, `src/koru/decision_engine.py`

> Current-state note: this ADR records the phased design that was implemented
> in May 2026. The former in-repository `korullm/` source root has since been
> extracted; current Koru imports the published `korullm` dependency. Module
> rows below describe their phase-time role unless an explicit current path is
> shown.

## Kontekst

Obecna pętla autonomiczna koru (`autonomous_cycle.py`) podejmuje decyzje wyłącznie
na podstawie prostych heurystyk:

1. **scan** → wykryj sygnały (code2llm, testy, linting)
2. **queue** → wykonaj tickety z planfile (FIFO)
3. **drive** → wklej prompt do IDE chat
4. **wait** → cooldown, streak, ponów

**Brak zamkniętej pętli weryfikacji** — koru nie wie, czy IDE wykonało zadanie.
**Brak inteligentnego planowania** — decyzje to proste `if/elif` w heurystykach.
**Brak refleksji** — `reflection_policy.py` istnieje, ale nie wywołuje LLM.

Cel: koru samo podejmuje decyzje, korzystając z trzech źródeł inteligencji:

| Źródło | Rola | Kiedy |
| --- | --- | --- |
| **OpenRouter LLM** | Planner + evaluator (strategia, priorytetyzacja, ocena) | Przed drive, po drive, na idle |
| **Heurystyki** | Szybkie decyzje (cooldown, test health, git diff) | Zawsze, zero-latency |
| **IDE LLM** | Executor (generuje kod, odpowiada na prompt) | Drive via autopilot |

## Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                    koru autonomous loop                     │
│                                                             │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │ Heuristic   │   │ Planning LLM │   │ Verification     │  │
│  │ Engine      │   │ (OpenRouter) │   │ Engine           │  │
│  │             │   │              │   │                  │  │
│  │ • test HP   │   │ • plan next  │   │ • git diff       │  │
│  │ • git dirty │   │ • evaluate   │   │ • test results   │  │
│  │ • cooldown  │   │ • prioritize │   │ • chat history   │  │
│  │ • streak    │   │ • redrive    │   │ • code2llm       │  │
│  │ • wup       │   │ • reflect    │   │ • file changes   │  │
│  └──────┬──────┘   └──────┬───────┘   └────────┬─────────┘  │
│         │                 │                    │            │
│         └────────┬────────┘                    │            │
│                  ▼                             │            │
│         ┌────────────────┐                     │            │
│         │ Decision       │◄────────────────────┘            │
│         │ Arbiter        │                                  │
│         │                │                                  │
│         │ merge signals  │                                  │
│         │ → ActionPlan   │                                  │
│         └───────┬────────┘                                  │
│                 ▼                                           │
│         ┌────────────────┐         ┌─────────────────────┐   │
│         │ Drive Engine   │───────►│ IDE LLM (executor)  │   │
│         │ (autopilot)    │◄───────│ Cursor/Windsurf/... │   │
│         └────────────────┘        └─────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Nowe moduły

### 1. `src/koru/autonomy/planning_llm.py` — Planning LLM

Odpowiada za wywołania OpenRouter API. Trzy tryby:

```python
class PlanningLlm:
    """OpenRouter-backed planning/evaluation LLM."""

    def plan_next_action(self, context: CycleContext) -> ActionPlan:
        """Given project state, decide what to do next."""

    def evaluate_drive_result(self, context: DriveResult) -> Evaluation:
        """After IDE drive, assess if the task was completed."""

    def generate_better_prompt(self, ticket: Ticket, history: list[DriveAttempt]) -> str:
        """Generate improved prompt when previous attempts failed."""

    def reflect_on_chat(self, messages: list[ChatMessage]) -> Reflection:
        """Interpret ambiguous chat state."""
```

**Konfiguracja** w `koru.yaml`:

```yaml
autonomy:
  strategy:
    planning_assistant:
      enabled: true
      provider_order: [openrouter, ide_llm]
      openrouter:
        model: openrouter/qwen/qwen3-coder-next
        api_key_env: OPENROUTER_API_KEY
        mode: prompt_or_explicit_call
        max_tokens: 4096
        temperature: 0.2
        budget_per_cycle_usd: 0.01
```

### 2. `src/koru/autonomy/verification_engine.py` — Verification Engine

Zamknięta pętla: po drive sprawdza, czy IDE faktycznie wykonało pracę.

```python
class VerificationEngine:
    """Post-drive verification: did the IDE actually do the work?"""

    def verify_drive_outcome(self, before: Snapshot, after: Snapshot) -> Verdict:
        """Compare project state before and after drive."""

    def collect_evidence(self, project: Path) -> Evidence:
        """Gather git diff, test results, chat history, code2llm delta."""
```

**Sygnały weryfikacji:**

| Sygnał | Źródło | Waga |
| --- | --- | --- |
| `git_diff_nonempty` | `git diff --stat` | Wysoka |
| `tests_pass` | WUP/TestQL | Wysoka |
| `chat_response_received` | chat history watcher | Średnia |
| `code2llm_cc_reduced` | code2llm delta | Średnia |
| `file_mtime_changed` | filesystem | Niska |

### 3. `src/koru/autonomy/decision_arbiter.py` — Decision Arbiter

Scala sygnały z heurystyk, planning LLM i verification engine.

```python
class DecisionArbiter:
    """Merge signals from heuristics, LLM, and verification into actions."""

    def decide(self, signals: Signals) -> ActionPlan:
        """
        Priority:
        1. Heuristics veto (test failure → stop, cooldown → wait)
        2. Verification verdict (task done → close ticket, not done → redrive)
        3. Planning LLM recommendation (prioritize, switch, escalate)
        """
```

**ActionPlan types:**

```python
@dataclass
class ActionPlan:
    action: Literal[
        "drive_ticket",        # paste prompt to IDE for ticket work
        "redrive_improved",    # retry with LLM-generated better prompt
        "close_ticket",        # verification passed, mark done
        "escalate_ticket",     # too many failures, mark input
        "switch_ticket",       # current ticket stuck, try another
        "run_discovery",       # queue empty, scan for new work
        "wait",                # cooldown active
        "reflect",             # ask LLM to interpret chat state
    ]
    ticket_id: str | None = None
    prompt: str | None = None
    reason: str = ""
    evidence: dict = field(default_factory=dict)
```

## Fazy implementacji

### Faza 1: Verification Engine (zero LLM cost) ✅ DONE
- `verification_engine.py`: git diff + test results + chat history → Verdict
- Hook do `autonomous_cycle.py`: `_take_pre_drive_snapshot()` + `_handle_post_drive_verification()`
- Po drive: zbierz evidence, oceń heurystycznie, emituj `DriveVerdict` event
- Jeśli brak zmian po 2 drive'ach → `escalate_ticket`
- Jeśli testy przechodzą + git diff → `close_ticket` (z opcją `planfile ticket done`)
- Nowe pola w `AutoloopState`: `last_drive_snapshot`, `last_drive_verdict`, `drive_count_for_ticket`
- Testy: `tests/test_verification_engine.py` (20 testów)

### Faza 2: Decision Arbiter (heurystyki only) ✅ DONE
- `decision_arbiter.py`: `ArbiterSignals` → `decide()` → `ActionPlan`
- ActionPlan jako ustrukturyzowany output emitowany jako `ActionPlan` event
- Zintegrowany w `_handle_post_drive_verification()` — advisory mode
- Telemetria: `DriveVerdict` + `ActionPlan` events w każdym cyklu po drive
- Nowe pole w `AutoloopState`: `last_drive_action_plan`
- Testy: `tests/test_decision_arbiter.py` (18), `tests/test_verification_cycle_integration.py` (10)

### Faza 3: Planning LLM (OpenRouter) ✅ DONE
- `planning_llm.py`: OpenRouter API client z `BudgetTracker`
- `evaluate_drive_result()`: evidence + heuristic verdict → `LlmEvaluation`
- `generate_better_prompt()`: stagnant ticket → improved prompt text
- `plan_next_action()`: advisory `LlmActionAdvice` (queue state → action)
- Budget guard: `budget_per_cycle_usd` + `budget_per_hour_usd` z auto-reset
- Fallback: jeśli OpenRouter niedostępny/over budget → heurystyki only (zero crash risk)
- Zintegrowany w `_handle_post_drive_verification()` z try/except (fail-safe)
- Env: `KORU_PLANNING_LLM` (on/off), `KORU_PLANNING_LLM_MODEL`, `KORU_PLANNING_LLM_TIMEOUT`
- Emituje eventy: `LlmEvaluation`, `LlmImprovedPrompt`
- Testy: `tests/test_planning_llm.py` (38 testów)

### Faza 4: Reflection + Self-Improvement ✅ WIRED (advisory)
- `reflect_on_chat()` — OpenRouter-native chat reflection (dodane do `planning_llm.py`)
- Runtime chat reflection: `autonomous_cycle_chat_activity.py` używa `llx` first, fallback do `planning_llm.reflect_on_chat()`
- Gating refleksji: aktywne gdy dostępne `llx` **lub** (`KORU_PLANNING_LLM` + `OPENROUTER_API_KEY`)
- `propose_strategy_tuning()` — podpięte do cyklu jako event `LlmStrategyTuningAdvice` (advisory)
- `prioritize_tickets()` — podpięte do cyklu jako event `LlmTicketPriority` (advisory)
- Feature flags (domyślnie OFF):
  - `KORU_PLANNING_LLM_STRATEGY_TUNING=1`
  - `KORU_PLANNING_LLM_PRIORITIZE_TICKETS=1`
- Nowe typy: `LlmReflection`, `StrategyTuning`, `TicketPriority`
- Wszystkie funkcje fail-safe (None jeśli LLM niedostępny/over budget)
- Testy: `tests/test_planning_llm.py` (+16 nowych testów Phase 4), `tests/test_autonomous.py` (fallback + advisory hooks)

## Integracja z istniejącym kodem

| Istniejący moduł | Zmiana | Faza |
| --- | --- | --- |
| `autonomous_cycle_orchestrator.py` | Konsumuj ActionPlan zamiast inline logic | 2 |
| `autonomous_cycle_chat_activity.py` | Verification engine ocenia chat events | 1 |
| `decision_engine.py` | Dodaj planning_llm jako opcjonalne źródło | 3 |
| `reflection_policy.py` | Wywołaj `planning_llm.reflect_on_chat()` | 4 |
| `autonomy_strategy/defaults.py` | Rozszerz `planning_assistant` config | 3 |
| published `korullm` dependency | Model strategy and typed invocation boundary (formerly local `korullm/`) | 3 |
| `autonomous_cycle_drive_retry.py` | Verification verdict wpływa na retry | 1 |
| `autonomy/post_run_verify.py` | Integracja z verification_engine | 1 |

## Bezpieczeństwo i limity

- **Budget guard**: max USD per cycle, per hour, per session
- **Rate limiting**: max OpenRouter calls per minute
- **Fallback**: OpenRouter unavailable → heuristics only (graceful degradation)
- **Audit trail**: każde wywołanie LLM logowane do telemetrii
- **No auto-merge**: LLM nigdy nie commituje bez weryfikacji testów
- **No credential exposure**: API key tylko z env var, nigdy w logach

## Metryki sukcesu

- **Ticket completion rate**: % ticketów zamkniętych automatycznie (cel: >50%)
- **Drive efficiency**: zmniejszenie redrive'ów (cel: <2 drive'y na ticket)
- **Verification accuracy**: false positive/negative rate zamykania ticketów
- **LLM cost per ticket**: średni koszt OpenRouter na zamknięty ticket

# Jak włączyć Phase 4 (runtime)

Minimalna konfiguracja środowiska:

```bash
export OPENROUTER_API_KEY=sk-or-...
export KORU_PLANNING_LLM=1
```

Włączenie advisory hooków (domyślnie OFF):

```bash
export KORU_PLANNING_LLM_PRIORITIZE_TICKETS=1
export KORU_PLANNING_LLM_STRATEGY_TUNING=1
```

Uruchomienie pętli:

```bash
koru autonomous up --max-cycles 5 --sleep-seconds 30
```

Oczekiwane eventy telemetryczne:
- `LlmTicketPriority`
- `LlmStrategyTuningAdvice`
- `autopilot_llx_reflection` (z `llx` lub fallback OpenRouter)

Uwaga: hooki Phase 4 są advisory-only (brak automatycznej mutacji `koru.yaml`).

## Rollback / disable

Szybkie wyłączenie advisory hooków Phase 4:

```bash
export KORU_PLANNING_LLM_PRIORITIZE_TICKETS=0
export KORU_PLANNING_LLM_STRATEGY_TUNING=0
```

Pełny fallback do heurystyk (bez Planning LLM):

```bash
export KORU_PLANNING_LLM=off
```

Efekt: pętla działa dalej przez Verification Engine + Decision Arbiter + heurystyki, bez wywołań OpenRouter.

## Decyzja

Implementować fazowo (1→2→3→4). Każda faza jest samodzielna i daje
mierzalną wartość. Faza 1 jest zero-cost (brak LLM), Faza 3 wymaga
`OPENROUTER_API_KEY`.

## Konsekwencje

- Koru staje się prawdziwie autonomiczny: planner + executor + verifier
- OpenRouter koszt ~$0.01/ticket przy Qwen3-coder-next
- IDE LLM pozostaje executorem (generuje kod), koru jest orchestratorem
- Heurystyki zawsze mają veto (bezpieczeństwo)
- Istniejąca architektura (`autonomy_strategy`, `decision_engine` and the
  published `korullm` dependency) is extended rather than replaced
