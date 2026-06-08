# nlp2coru

NLP adapter for CORU control DSL.

- `to_dsl` maps prompt text to control commands (`ENSURE`, `STATUS`, `AUTO`, ...)
- `apply` executes generated DSL via `dsl2coru`
- optional LLM planner (`--llm`) delegates to `litellm` for richer mapping
