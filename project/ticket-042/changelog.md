# Changelog

- Hardened the IDE matrix fixture with immutable Python and uv inputs, frozen
  lock synchronization, and hermetic runtime defaults.
- Added an exhaustive regression boundary covering seven Dockerfile-like inputs,
  eleven Compose declarations, remote Git commits, immutable images and
  lock-driven non-root installs.
