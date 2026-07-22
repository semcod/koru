"""Model router: turn a failed attempt into the next step, per the design table.

The router is the piece that makes a repair run survive a provider policy block
— it treats the block as an operational event and picks another model on the
same run, rather than failing the ticket.
"""

from __future__ import annotations

from dataclasses import dataclass

from koru.repair_runs import model_router as mr


@dataclass
class _Attempt:
    """Minimal stand-in for ModelAttempt — the router only reads ``.model``."""

    model: str


REGISTRY = [
    mr.ModelSpec(id="primary", model="anthropic/opus", provider="anthropic", max_attempts=2),
    mr.ModelSpec(id="fallback-policy", model="openai/gpt", provider="openrouter", max_attempts=3),
    mr.ModelSpec(id="fallback-context", model="google/gemini", provider="openrouter", max_attempts=1),
]


def test_policy_block_switches_to_the_next_model_not_fail():
    d = mr.route(
        mr.PROVIDER_POLICY_BLOCK,
        registry=REGISTRY,
        attempts=[_Attempt("anthropic/opus")],
        last_model=REGISTRY[0],
    )
    assert d.verb == mr.SWITCH_MODEL
    assert d.next_model.model == "openai/gpt"  # the next configured model, not the blocked one
    assert d.retryable is True
    assert d.escalate is False


def test_timeout_retries_the_same_model_once_then_switches():
    first = mr.route(
        mr.PROVIDER_TIMEOUT, registry=REGISTRY,
        attempts=[_Attempt("anthropic/opus")], last_model=REGISTRY[0],
    )
    assert first.verb == mr.RETRY_SAME_MODEL
    assert first.next_model.model == "anthropic/opus"

    # Same model's budget (2) now spent → move on.
    spent = [_Attempt("anthropic/opus"), _Attempt("anthropic/opus")]
    second = mr.route(mr.PROVIDER_TIMEOUT, registry=REGISTRY, attempts=spent, last_model=REGISTRY[0])
    assert second.verb == mr.SWITCH_MODEL
    assert second.next_model.model == "openai/gpt"


def test_invalid_structured_output_changes_model():
    d = mr.route(
        mr.INVALID_STRUCTURED_OUTPUT, registry=REGISTRY,
        attempts=[_Attempt("anthropic/opus")], last_model=REGISTRY[0],
    )
    assert d.verb == mr.SWITCH_MODEL


def test_non_model_remedies_do_not_spend_a_model():
    cases = {
        mr.CONTEXT_LENGTH_EXCEEDED: mr.REDUCE_CONTEXT,
        mr.MISSING_FACT: mr.RUN_PROBE,
        mr.PATCH_INVALID: mr.REGENERATE_PATCH,
        mr.VERIFICATION_FAILED: mr.REPAIR_ITERATION,
        mr.CAPABILITY_UNAVAILABLE: mr.DISCOVERY_PROBE,
        mr.WORKSPACE_DRIFT: mr.REMANIFEST_OR_STOP,
    }
    for code, verb in cases.items():
        d = mr.route(code, registry=REGISTRY, attempts=[], last_model=REGISTRY[0])
        assert d.verb == verb, code
        assert d.next_model is None, code  # the model is not the problem
        assert d.escalate is False, code


def test_runtime_policy_denied_is_forbidden_not_a_model_switch():
    d = mr.route(mr.RUNTIME_POLICY_DENIED, registry=REGISTRY, attempts=[], last_model=REGISTRY[0])
    assert d.verb == mr.FORBIDDEN_STOP
    assert d.next_model is None
    assert d.escalate is True
    assert d.retryable is False


def test_all_models_blocked_is_exhausted_not_do_anything():
    # Every model spent to its budget.
    attempts = (
        [_Attempt("anthropic/opus")] * 2
        + [_Attempt("openai/gpt")] * 3
        + [_Attempt("google/gemini")] * 1
    )
    d = mr.route(mr.PROVIDER_POLICY_BLOCK, registry=REGISTRY, attempts=attempts, last_model=REGISTRY[2])
    assert d.verb == mr.MODEL_EXHAUSTED
    assert d.escalate is True
    assert d.next_model is None


def test_routing_is_deterministic_for_a_given_history():
    args = dict(registry=REGISTRY, attempts=[_Attempt("anthropic/opus")], last_model=REGISTRY[0])
    a = mr.route(mr.PROVIDER_POLICY_BLOCK, **args)
    b = mr.route(mr.PROVIDER_POLICY_BLOCK, **args)
    assert a == b


def test_switch_never_re_picks_the_failing_model():
    # Only the last model has budget left, and it just policy-blocked: do not
    # re-pick it — that would just repeat the block.
    single = [mr.ModelSpec(id="only", model="anthropic/opus", provider="anthropic", max_attempts=1)]
    d = mr.route(
        mr.PROVIDER_POLICY_BLOCK, registry=single,
        attempts=[_Attempt("anthropic/opus")], last_model=single[0],
    )
    assert d.verb == mr.MODEL_EXHAUSTED


def test_decision_serialises_to_a_ledger_event():
    d = mr.route(
        mr.PROVIDER_POLICY_BLOCK, registry=REGISTRY,
        attempts=[_Attempt("anthropic/opus")], last_model=REGISTRY[0],
    )
    event = d.as_event()
    assert event["verb"] == mr.SWITCH_MODEL
    assert event["next_model_id"] == "fallback-policy"
    assert event["escalate"] is False


# ── classify_failure: raw invocation result → canonical code ────────────────

def test_classify_success_is_none():
    assert mr.classify_failure(0, stderr="anything") is None


def test_classify_policy_block_from_provider_text():
    for text in [
        "Error: request was refused by content policy",
        "the model declined to answer",
        "blocked by safety filter",
        "This request is not allowed",
    ]:
        assert mr.classify_failure(1, stderr=text) == mr.PROVIDER_POLICY_BLOCK, text


def test_classify_timeout_and_unavailable_and_context():
    assert mr.classify_failure(1, stderr="deadline exceeded, request timed out") == mr.PROVIDER_TIMEOUT
    assert mr.classify_failure(1, stderr="503 Service Unavailable (overloaded)") == mr.PROVIDER_UNAVAILABLE
    assert mr.classify_failure(1, stderr="429 rate limit reached") == mr.PROVIDER_UNAVAILABLE
    assert mr.classify_failure(1, stderr="maximum context length exceeded") == mr.CONTEXT_LENGTH_EXCEEDED


def test_classify_invalid_structured_output():
    assert mr.classify_failure(1, stdout="{not valid json", stderr="json decode error") == mr.INVALID_STRUCTURED_OUTPUT


def test_classify_runtime_policy_denied_is_distinct_from_provider_block():
    # A runtime denial (our own policy) must not be treated as a provider block —
    # switching models must NOT bypass it.
    assert mr.classify_failure(1, stderr="operation forbidden by policy: risk ceiling") == mr.RUNTIME_POLICY_DENIED


def test_classify_unknown_failure_is_none_router_handles_conservatively():
    assert mr.classify_failure(1, stderr="some novel error nobody mapped") is None


def test_classifier_feeds_the_router_end_to_end():
    # The bridge: raw result → code → decision. A policy block routes to a switch.
    code = mr.classify_failure(1, stderr="refused by content policy")
    decision = mr.route(code, registry=REGISTRY, attempts=[_Attempt("anthropic/opus")], last_model=REGISTRY[0])
    assert decision.verb == mr.SWITCH_MODEL
