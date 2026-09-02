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
- Ticket-052 removes the final nine project-analysis outputs. All 49 paths in
  the generated-state baseline are now out of source control; CI artifact
  publication remains the final stage acceptance item.
