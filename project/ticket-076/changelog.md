# Changelog

- Planned one canonical event-store location factory and framed-protobuf replay decoder.
- Unified native and compatibility store path construction without changing on-disk locations.
- Reused one framed-protobuf decoder for direct reads and replay.
- Added location, format, ordering, empty-store and truncated-tail regression coverage.
