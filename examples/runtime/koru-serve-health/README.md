# Runtime — `koru serve` + `/health`

Bootstraps a tiny koru project, starts **`koru serve --no-open`** on
`127.0.0.1:18765`, then **`curl`**s the documented **`GET /health`** JSON.

## Run

```bash
./run-docker.sh
```

## Note

The dashboard binds **`127.0.0.1`** by default; this is correct for a
single-container smoke. Use `--host 0.0.0.0` only when another container must
reach the server.
