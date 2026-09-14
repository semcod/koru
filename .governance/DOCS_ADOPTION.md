# Documentation gate: consumer preparation

Adopted source: [wellmanifest/docs 0.5.0](https://github.com/wellmanifest/docs/tree/71c296aab28bceec709722f59078ca86ac48dca7).
The `.governance/docs.json` pin and `docs_gate.py` adapter are consumer-side
preparation, not proof that a protected executor invokes the gate.

## Local preflight and final validation

An operator supplies a local published standard checkout/install. The adapter
checks exact SHA-256 hashes of all four runtime artifacts and executes a fresh
temporary projection of those verified bytes. It never imports adjacent cache
or arbitrary source files, fetches code, or accepts a candidate-selected pin.
The canonical checker owns all document, redirect and DSL rules; Koru does not
reimplement them. Missing or modified runtime is a failure.

```bash
python3 .governance/docs_gate.py prepare --root . \
  --standard-root "$DOCS_STANDARD_ROOT" --kind feature --id consumer-pilot \
  --deliverable docs/FEATURE/CONSUMER_PILOT.md
```

Stop on a nonzero exit before generating a document. After writing and staging
the intended files, validate against the independently observed base commit:

```bash
python3 .governance/docs_gate.py final --root . \
  --standard-root "$DOCS_STANDARD_ROOT" --base "$TRUSTED_BASE_SHA"
```

Use `--policy-dsl-root "$POLICY_DSL_ROOT"` for formal FEATURE/BUGFIX contracts;
the canonical lock verifies that dependency. DSL references do not execute tests.
Existing legacy documents outside automatic discovery are not certified by PASS.

## Canary and deployment boundary

```bash
KORU_DOCS_STANDARD_ROOT="$DOCS_STANDARD_ROOT" \
python3 -m unittest discover -s .governance/tests -p test_docs_gate.py
```

Canaries use the three current Koru compact guides and two redirect maps in
temporary Git fixtures. They test both phases, absent adoption, wrong pin,
runtime tampering/symlink, absent index, removed metadata/target and invalid base.
Without the environment variable corpus canaries are explicitly skipped, not PASS.

At the 2026-09-14 observation, Koru's OneDev profile does not call the docs
checker. GitHub has no docs trust variables. Existing `standard packs /
conformance` does not prove docs enforcement. The OneDev configuration has
independent unfinished edits: preserve them and coordinate its owner.

Before closing [campaign issue 169](https://github.com/semcod/koru/issues/169),
the protected executor must independently install the published runtime and
select this pin, run the checker at the exact consumer base/head, and reject
negative canaries through the actual generator and CI paths. It must not trust
the candidate's copy of this adapter or adoption file to choose enforcement.
Use the existing OneDev/Validator process, not a self-authored success status.
Do not enable disabled Issues in other repositories or rewrite old ticket states.
Rollback preserves documents and restores the preceding adopter configuration.
