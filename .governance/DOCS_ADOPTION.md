# Documentation gate: deployed CI and remaining pilot

Adopted source: [wellmanifest/docs 0.5.0](https://github.com/wellmanifest/docs/tree/71c296aab28bceec709722f59078ca86ac48dca7).
The `.governance/docs.json` pin and `docs_gate.py` adapter support local checks.
Protected OneDev enforcement uses its independently installed checker, not the
candidate adapter or candidate-selected runtime. Deployment and consumer CI
results are separate evidence; neither certifies the entire documentation fleet.

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

## Local corpus canaries

```bash
KORU_DOCS_STANDARD_ROOT="$DOCS_STANDARD_ROOT" \
python3 -m unittest discover -s .governance/tests -p test_docs_gate.py
```

Canaries use the three current Koru compact guides and two redirect maps in
temporary Git fixtures. They test both phases, absent adoption, wrong pin,
runtime tampering/symlink, absent index, removed metadata/target and invalid base.
Without the environment variable corpus canaries are explicitly skipped, not PASS.

## Protected deployment

On 2026-09-14, both OneDev PR services were deployed from independently reviewed
[onedev-agent PR 351](https://github.com/subactor/onedev-agent/pull/351), merge
`10960571427501ff0fc833d65006e85ba2ee689c`. The selected image is
`ifuri-onedev-agent:koru-docs-350-required-canaries`, immutable image ID
`sha256:2d14f256e784fc8f390ef53c5fa5038375c9772e3b229c4b10484a440439d409`.

Koru's protected profile now starts with
`python -I -B /app/docker/pr/check-koru-docs.py`, before its existing regression
suite. The image independently pins Docs 0.5.0 and Policy DSL revision
`7109aee92c2bb7ac2db8e3b0b4ddd7ded4750257`. Missing or altered artifacts fail;
the PR cannot choose weaker enforcement through its own adapter or adoption pin.
Existing required checks and independent Validator approval remain mandatory.

Deployment readback confirmed both services running the exact image and mounted
profile, with unchanged environment, mounts, network and security settings.
All 15 mandatory image integration canaries passed in that image; these cover
the protected checker, not the real document-generation pipeline. Unlike the
optional local corpus suite, absent image artifacts are failures, not skips.

The operator binding is `onedev-agent/.subactor/deployments/koru-docs-350/`:
`compose.yaml` selects only the two PR services; `before.json`, `after.json` and
`receipt.json` retain local observations. `rollback.yaml` selects their preceding
image; the saved configuration archive preserves the preceding profile.
These host-local records are audit evidence, not portable approval credentials.
Rollback must preserve unrelated configuration edits and documents. Do not use
the global Compose image default, restart unrelated services or delete queues.

## Remaining acceptance

Before closing [campaign issue 169](https://github.com/semcod/koru/issues/169),
record an actual post-deployment Koru PR result bound to its exact base/head,
showing the protected docs command and the existing checks. Ticket-136's
documentation PR is the first requested consumer canary, not an advance claim
of its success; keep the observed result in the campaign and external receipt.

Still required: integrate pre-generation validation into the real generator,
demonstrate negative cases through that path, then roll out bounded repository
pilots and review historical duplicates without losing old links or task intent.
Current local corpus coverage is three compact guides and two redirect maps;
legacy documents outside discovery and other repositories remain uncertified.
Do not enable disabled Issues or rewrite historical ticket states to imply
completion. Use the existing OneDev/Validator process, never self-authored status.
