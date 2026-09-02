# Agent plan

1. Adopt completed upstream revisions by immutable commit.
2. Pin nested Python and uv images and synchronize frozen locks.
3. Build every affected image without cache and run targeted smoke checks.
4. Publish through the protected validator process.
