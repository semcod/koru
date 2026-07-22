# ProposalEnvelope v1 — deterministyczna granica wyjścia LLM

`ProposalEnvelope` jest małym JSON DSL-em pomiędzy modelem a wykonawcami Koru.
Nie jest planem wykonania ani grantem. Model proponuje nazwany intent i
ograniczony artefakt; Koru sprawdza strukturę oraz hashe, a dopiero później
osobne capability contract, dry-run i grant mogą dopuścić wykonanie.

Kanoniczny schema runtime:
[`../src/koru/data/proposal-envelope-v1.schema.json`](../src/koru/data/proposal-envelope-v1.schema.json).
Walidator i builder:
[`../src/koru/proposal_envelope.py`](../src/koru/proposal_envelope.py).

## Kształt

```json
{
  "schema_version": "1.0",
  "intent_pack": {"id": "development.propose_patch", "version": "1.0"},
  "slots": {"ticket_id": "DEV-1"},
  "artifact": {"kind": "unified_diff", "content": "diff --git ..."},
  "bindings": {
    "input_hash": "<sha256>",
    "prompt_schema_hash": "<sha256>"
  },
  "provenance": {"provider": "z.ai", "model": "glm-4.7"},
  "hashes": {
    "artifact_sha256": "<sha256>",
    "proposal_sha256": "<sha256>"
  }
}
```

Używaj `build_proposal_envelope(...)`; builder wylicza oba hashe. Parser
akceptuje wyłącznie dokładny JSON — bez markdown fences i tekstu przed/po.
`artifact_sha256` wiąże kanoniczne `{kind, content}`, a `proposal_sha256`
wiąże cały envelope poza samą sekcją `hashes`.

## Authority jest poza DSL-em

Schema ma `additionalProperties: false`. Także zagnieżdżone sloty są odrzucane,
jeżeli próbują wprowadzić `uri`, `transport`, `vault`, `secret`, `approval`,
`executor` lub `capability`. Te dane pochodzą z wersjonowanego Intent Packa,
capability registry i kontraktu aktora, nigdy z odpowiedzi modelu.

Queue rozpoznaje obecnie envelope z artefaktem `unified_diff`, weryfikuje jego
binding i dopiero potem uruchamia istniejący parser diff/preflight. Naruszenie
kontraktu daje strukturalny kod `no_valid_artifact` i najwyżej jeden retry.
Bare unified diff pozostaje chwilowo wejściem zgodności podczas migracji
producentów tillm/IDE; jego usunięcie jest ostatnią częścią P0-2.
