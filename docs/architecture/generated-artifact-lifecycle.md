# Generated artifact lifecycle

Koru keeps generated analysis, coverage, tree snapshots and release media out
of source control. `config/artifact-registry.json` is the small checked-in
control record: it binds the baseline commit, generator versions, path groups,
byte counts and SHA-256 digests. Generated output has no authority over runtime
or governance decisions.

## Reproduce locally

Run generators from a clean checkout with the versions recorded in the
registry. The commands below write only ignored paths:

```bash
code2llm . -f all -o project --no-chunk --exclude '*.md'
sumd map . --stdout > SUMD.md
python -m coverage run -m pytest
python -m coverage json -o coverage.json
./tree.sh > tree.txt
```

Plugin analysis uses the same Code2LLM version and writes to
`.tmp/code2llm-plugins`. Release media is produced from the approved demo
source in CI; it is never reconstructed from untrusted repository output.

## Verify a generated set

For each artifact group, sort its paths lexicographically, run `sha256sum` on
the files and hash those records once more. This is the registry's
`digestInput` contract. Compare the resulting digest with the group entry;
fresh output may differ only when the generator, inputs or declared version
changed.

## Recover the accepted baseline

The pre-cleanup baseline is immutable Git commit
`f5692855605ff3a7fae9ec671ebb7b5537dfd2a8`. Recover a specific file without
rewriting history, for example:

```bash
git show f5692855605ff3a7fae9ec671ebb7b5537dfd2a8:project/map.toon.yaml > project/map.toon.yaml
```

CI publishes regenerated analysis, coverage and available release media as
retained workflow artifacts. Those artifacts are evidence and diagnostics,
not inputs that grant execution or merge authority.

## Migration progress

- Ticket-048 removed the root analysis, coverage, Code2LLM, tree and release
  media groups.
- Ticket-050 removed the first fourteen plugin-analysis files.
- Ticket-051 removed the remaining four plugin-analysis files and the first ten
  project-analysis files.
- Ticket-052 removed the final nine project-analysis outputs. All 49 files in
  the generated-state baseline, totalling 17,172,638 bytes, are now out of
  source control.
- Ticket-053 replaced the write-capable weekly automation with the read-only
  `.github/workflows/sumr-weekly.yml` artifact workflow. Proof run
  `33612230881` published separate analysis, coverage and hash-verified media
  artifacts with 14-day retention.
- Ticket-054 made the plan contract verify every exact and wildcard registry
  path against the Git index. Its 8 tests and 68 subtests passed with no
  generated output tracked.

The `repository.generated_state` stage is complete. Relative to the plan's
tracked-checkout baseline, the repository at merge commit `8c36ee13` is down
16,266,309 bytes and 127,412 net tracked lines. The net figures include new
registry, tests and delivery evidence; the immutable registry remains the
source of truth for the removed generated payload itself.
