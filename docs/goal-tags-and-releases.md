# Goal: git tags vs GitHub Releases

Why [github.com/semcod/koru/releases](https://github.com/semcod/koru/releases)
can show **v0.1.215** as “latest” while the repo already has tags like
**v0.1.398**.

## Two different things

| Concept | What it is | Created by goal? |
| ------- | ---------- | ---------------- |
| **Git tag** (`refs/tags/vX.Y.Z`) | Pointer on a commit | Yes — `create_tag()` + `git push origin vX.Y.Z` |
| **GitHub Release** | Product page + notes + assets under `/releases` | **Only in special cases** (see below) |

The URL `/releases/tag/v0.1.215` is a **Release object**.  
A tag can exist without a Release; the Releases “Latest” badge then stays on
the last Release ever created.

Verified (2026-07-17):

- Tag `v0.1.398` exists on `origin` (`git ls-remote --tags`).
- `GET /repos/semcod/koru/releases/tags/v0.1.398` → **404** (no Release).
- `GET /repos/semcod/koru/releases/latest` → **v0.1.215** (last Release, 2026-05-22).

So **tags were changing**; the **Releases UI was not**.

## What goal does today

1. **Version bump** into `VERSION` / `pyproject.toml` / `package.json` when
   package **source** changed (not pure docs-only commits).
2. **Annotated git tag** `v{version}` unless:
   - `--no-tag`, or
   - publish skipped for *no package source changes*
     (`⏭ Skipping tag v… — no package source changes to release`).
3. **Push** branch + tag to `origin`.
4. **PyPI publish** only when `publishing.enabled` and strategies allow it.
5. **GitHub Release** historically only via
   `publishing.fallback.github_release` when **PyPI upload is blocked**
   (`try_github_fallback` → `gh release create`).

Koru’s `goal.yaml` had:

```yaml
publishing:
  enabled: false   # no PyPI path → fallback almost never runs
  fallback:
    github_release:
      enabled: true   # only used if PyPI is attempted and blocked
```

That combination produces many new **tags**, almost no new **Releases** after
the last time the fallback (or a manual `gh release create`) ran — around
**v0.1.215**.

## Fix (goal + koru config)

### Goal (`semcod/goal`)

New flag:

```yaml
publishing:
  fallback:
    github_release:
      create_on_tag: true   # default false (backward compatible)
```

When a version tag is created and pushed, goal calls
`try_github_release_on_tag()` → `gh release create` (and optional dist assets).

Requires:

- `gh` CLI installed and authenticated, or
- `GITHUB_TOKEN` / env named by `token_env` with `repo` scope.

### Koru `goal.yaml`

```yaml
publishing:
  fallback:
    github_release:
      enabled: true
      owner: semcod
      repo: koru
      create_on_tag: true
      token_env: GITHUB_TOKEN
```

### One-shot backfill (optional)

To create Releases for existing tags without re-publishing PyPI:

```bash
# example: create release for current VERSION if missing
TAG="v$(cat VERSION)"
gh release view "$TAG" -R semcod/koru >/dev/null 2>&1 \
  || gh release create "$TAG" -R semcod/koru \
       --title "koru $TAG" \
       --generate-notes
```

## Other reasons a tag is skipped on a given run

Even with tagging enabled:

| Situation | Effect |
| --------- | ------ |
| Only docs/CI/metadata staged | No version bump; often no tag (`no package source changes`) |
| `--no-tag` | Explicit skip |
| Tag already exists locally | Warning; no re-create |
| Push fails (auth/permissions) | Tag may stay local only |

## Related

- Goal push core: `goal/push/core.py` (`create_tag`, skip reasons)
- GitHub fallback: `goal/publish/github_fallback.py`
- Koru config: [`goal.yaml`](../goal.yaml)
- Docker / e2e map: [`docker-e2e-testing.md`](./docker-e2e-testing.md)
