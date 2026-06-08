# dsl2coru

Thin control-layer implementation for CORU. Input is a one-line text DSL, output is a
command result from the CORU domain layer.

```text
AUTO --ide windsrf --instance windsurf-main
LANE --ide cursor
STATUS
TEXT "run auto for cursor-main"
```

This package keeps parsing/dispatch separate from input adapters.
