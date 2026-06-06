# nlpshim

Shared NLP bridge utilities for `gillm` and `sillm`.
This package safely loads `nlp2dsl_sdk` and provides fallback heuristics when the SDK is not present.

## Relacja z nlp2dsl / Intract

`nlpshim` używa `nlp2dsl_sdk.workflow_from_text` — **nie** przechodzi przez `IntentIR` ani kontrakty Intract.

```mermaid
flowchart LR
    subgraph koru [koru / nlpshim]
        NB[NLPBridgeClient]
        SDK[nlp2dsl_sdk]
        FB[FallbackNLP2DSLClient]
    end

    subgraph full [pełna ścieżka — poza koru]
        IR[IntentIR]
        PLAN[ExecutionPlanIR]
        GATE[PlanStepGate / Intract]
    end

    NB --> SDK
    NB --> FB
    IR --> PLAN --> GATE
```

Aby w koru dostać walidację kontraktów, trzeba by routować przez `nlp2cmd_intent.analyze_query` + opcjonalnie `nlp2cmd.intract.plan_gate` zamiast samego SDK workflow.

Zob. [nlp2cmd/docs/architecture/intract-integration.md](https://github.com/wronai/nlp2cmd/blob/main/docs/architecture/intract-integration.md).
