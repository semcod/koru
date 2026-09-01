# Changelog

- Allocated ticket-032 for issue #37 and recorded its bounded delivery intent.
- Replaced both default adapter backends with their registered central SubLLM
  routes and removed local provider selection.
- Preserved injected backends, compatibility model arguments and deterministic
  offline fallbacks; added route and fallback regression coverage.
- Deferred the two package manifests and two README corrections to a bounded
  dependent ticket so the runtime change stays within the hard 15-file limit.
