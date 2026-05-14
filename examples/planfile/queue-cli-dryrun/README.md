# Planfile — queue CLI dry-run (no HTTP server)

Runs **`koru --queue --dry-run`** against a freshly `koru --init` project so the
`planfile` binary is exercised, but **no ticket side effects** occur.

This is the “CLI only” side of the matrix. For an HTTP health probe against a
long-running API process, see `examples/planfile/http-api-curl/`.

## Run

```bash
./run-docker.sh
```
