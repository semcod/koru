# dsl2koru

Koru control DSL: JSON Schema + protobuf + CQRS bus + EventStore.

```bash
# Legacy
dsl2koru -c 'VALIDATE_LANE IDE auto INSTANCE default'

# Subcommands
dsl2koru validate-schema
dsl2koru encode 'QUERY_REPAIR_HISTORY PROJECT .' --format protobuf
dsl2koru decode --input cmd.pb
dsl2koru replay --project .
```

Proto: `proto/dsl2koru/v1/` → `src/dsl2koru/v1/*_pb2.py` via `scripts/generate-proto.sh`.
