---
{
  "schema": "wellmanifest.docs/document/v2",
  "id": "voice-and-nl-control-bridge",
  "kind": "feature",
  "version": 1,
  "title": "Voice and natural language control bridge for Koru commands and queue",
  "status": "implemented",
  "owner": "semcod/koru",
  "scope": "repository",
  "updated": "2026-09-27",
  "source_revision": "2c82e2055feb269399c3081ec6750e5b5ee9b7df",
  "priority": "P2",
  "evidence": [
    "https://github.com/semcod/koru/commit/2c82e2055feb269399c3081ec6750e5b5ee9b7df",
    "https://github.com/semcod/koru/blob/main/src/koru/voice/bridge.py"
  ]
}
---

# Voice and natural language control bridge for Koru commands and queue

<!-- docs:section summary -->
## Summary

Koru 0.1.461 incorporates a voice and natural language bridge (`src/koru/voice/`) that translates spoken instructions and conversational prompts into executable CLI commands and Planfile queue tickets.

<!-- docs:section details -->
## Details

The voice and NL control layer expands operator interaction surfaces:

1. **Audio and conversational intake**: The `koru voice` command surface ingests voice streams or text prompts, dispatching them through local or API-based speech-to-text models.
2. **Intent classification and command translation**: Spoken intent is parsed against Koru command signatures (`koru scan`, `koru run`, `koru autonomous`, `koru queue`). Recognized intents trigger typed CLI invocations with validated flags.
3. **Conversational ticket generation**: Unstructured verbal bug reports or feature requests are synthesized into structured Planfile tickets, populating summary, priority, acceptance criteria, and initial code smell tags.
4. **Execution safety barriers**: Potentially destructive commands (e.g., branch deletion, worktree pruning, forced queue clears) require explicit interactive confirmation before dispatch.

<!-- docs:section validation -->
## Validation

Voice and NL functionality is verified by:
- Test coverage: `pytest tests/test_voice_bridge.py` verifies intent parsing accuracy, argument extraction, and command serialization.
- Dry-run validation: Running `koru voice parse --dry-run "<instruction>"` outputs translated CLI arguments without invoking subprocesses.

<!-- docs:section risks -->
## Risks

- **Acoustic and transcription ambiguity**: Accents or background noise can produce corrupted input strings. Mitigated by confidence scoring and confirmation prompts.
- **Intent hallucination**: LLM intent extraction could map ambiguous phrases to unintended commands. Controlled by strict grammar whitelists.
- **Next steps**: Integrate continuous microphone hotword detection for hands-free local operator control.
