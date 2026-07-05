"""Degradation contract: koru's gillm-absent fallback must match real gillm.

``koru.ide_adapters.gillm_recovery`` keeps a hand-written fallback copy of
gillm's recovery classifiers (the ``except ImportError`` block) so the operator
surface still works when gillm cannot be imported. That copy has already drifted
once (``no_calibrated_profile`` was retryable on the embedded-recovery path —
STARTER-028), producing a degraded surface that silently disagreed with the
real classifiers about whether a failure is worth retrying.

These tests pin the two things that must never drift between the real
``gillm.recovery`` and koru's fallback:

- **classification tokens** — every representative reason/message blob maps to
  the same ``FailureKind`` on both surfaces,
- **retryability** — the same set of kinds is treated as non-retryable.

A new token or a moved severity in gillm fails here until koru's fallback and
the real module agree again.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest

# Real surface — gillm is a core dependency, so this is the source of truth.
gillm_recovery = pytest.importorskip(
    "gillm.recovery",
    reason="gillm is a core dependency; install it to run the degradation contract",
)

_MODULE_NAME = "koru.ide_adapters.gillm_recovery"


def _load_fallback_surface():
    """Load a private copy of koru's recovery bridge with gillm import blocked.

    Setting ``sys.modules['gillm*'] = None`` makes ``import gillm.recovery`` raise
    ImportError, which forces the module's ``except ImportError`` fallback block to
    bind the hand-written classifiers. The freshly executed module is returned
    without disturbing the already-imported real one.
    """
    spec = importlib.util.find_spec(_MODULE_NAME)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)

    # Block gillm so the module's ``except ImportError`` fallback binds, and
    # register the fresh module under its real name during exec so @dataclass
    # can resolve ``cls.__module__`` via sys.modules. Both are restored after.
    blocked = {"gillm": None, "gillm.recovery": None}
    saved = {k: sys.modules.get(k) for k in list(blocked) + [_MODULE_NAME]}
    sys.modules.update(blocked)
    sys.modules[_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return module


# One representative reply per FailureKind the classifiers can emit. Kept as
# (label, reply-dict) so a failure names the case. Covers plugin, input,
# environment and the ok/unknown fall-throughs — plus the embedded-recovery
# variant that regressed in STARTER-028.
_CORPUS = [
    ("plugin_unavailable", {"ok": False, "message": "no connected autopilot plugin for ide=cursor"}),
    ("plugin_version_mismatch", {"ok": False, "message": "extension version mismatch"}),
    ("plugin_build_mismatch", {"ok": False, "message": "plugin build mismatch detected"}),
    ("submit_unverified", {"ok": False, "message": "submit could not be verified"}),
    ("input_busy_reason", {"ok": False, "submit_failure_reason": "chat_input_not_empty"}),
    ("input_busy_draft", {"ok": False, "message": "unrelated draft in composer"}),
    ("focus_failed", {"ok": False, "message": "focus failed for window"}),
    ("no_calibrated_profile_pl", {"ok": False, "message": "brak kalibracji dla cursor"}),
    ("no_calibrated_profile_en", {"ok": False, "message": "no calibrated profile for ide"}),
    ("no_calibrated_profile_embedded", {
        "ok": False,
        "message": "no calibrated profile for ide",
        "diagnostics": {"recovery": ["run koru autopilot calibrate"]},
    }),
    ("wayland_injection_blocked", {"ok": False, "message": "wayland injection blocked without ydotool"}),
    ("no_keyboard_backend", {"ok": False, "message": "no keyboard injection backend available"}),
    ("unknown", {"ok": False, "message": "totally novel failure text"}),
    ("ok", {"ok": True}),
]


@pytest.fixture(scope="module")
def fallback():
    return _load_fallback_surface()


@pytest.mark.parametrize("label,reply", _CORPUS, ids=[c[0] for c in _CORPUS])
def test_fallback_classification_matches_gillm(fallback, label, reply):
    real = gillm_recovery.diagnose_drive_reply(dict(reply))
    fb = fallback.diagnose_drive_reply(dict(reply))
    assert fb.kind == real.kind, (
        f"[{label}] fallback classified {fb.kind!r}, gillm classified {real.kind!r}"
    )


@pytest.mark.parametrize("label,reply", _CORPUS, ids=[c[0] for c in _CORPUS])
def test_fallback_retryability_matches_gillm(fallback, label, reply):
    real = gillm_recovery.diagnose_drive_reply(dict(reply))
    fb = fallback.diagnose_drive_reply(dict(reply))
    assert fb.retryable == real.retryable, (
        f"[{label}] fallback retryable={fb.retryable}, gillm retryable={real.retryable}"
    )


def test_non_retryable_kinds_are_pinned(fallback):
    """The non-retryable set is a hard contract, not an emergent property.

    Both surfaces must treat exactly these kinds as non-retryable. Adding a new
    terminal kind means updating this pin *and* both classifiers together.
    """
    expected_non_retryable = {
        "plugin_version_mismatch",
        "plugin_unavailable",
        "no_calibrated_profile",
    }
    probes = {
        "plugin_unavailable": {"ok": False, "message": "no connected autopilot plugin"},
        "plugin_version_mismatch": {"ok": False, "message": "version mismatch"},
        "no_calibrated_profile": {"ok": False, "message": "no calibrated profile"},
        "submit_unverified": {"ok": False, "message": "submit could not be verified"},
        "input_busy": {"ok": False, "submit_failure_reason": "chat_input_not_empty"},
    }
    for surface in (gillm_recovery, fallback):
        non_retryable = {
            kind for kind, reply in probes.items()
            if not surface.diagnose_drive_reply(dict(reply)).retryable
        }
        assert non_retryable == expected_non_retryable, (
            f"{surface.__name__} non-retryable set drifted: {non_retryable}"
        )
