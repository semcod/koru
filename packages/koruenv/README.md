# koruenv

`koruenv` is a standalone environment-control package for Koru IDE lanes.

Its purpose is to keep lane/socket/env orchestration outside the main `koru`
package, so environment policy can evolve independently.

## What it provides

- `koruenv env <ide> <instance>`: emit environment exports for one strict lane
- `koruenv run <ide> <instance> -- <command> ...`: run any command in lane env
- `koruenv status <ide> <instance>`: run `koru autopilot status --explain` in lane env
- `koruenv --log-format jsonl ...`: emit structured debug events

## Install (from monorepo)

```bash
pip install -e ./packages/koruenv
```

## Examples

```bash
eval "$(koruenv env windsurf windsurf-main)"
koruenv run windsurf windsurf-main -- koru autopilot daemon --project .
koruenv status windsurf windsurf-main
```

PowerShell:

```powershell
koruenv env vscode vscode-main --shell powershell | Invoke-Expression
koruenv status vscode vscode-main
```

## Logging contract

`koruenv` supports `--log-format human|jsonl`.

In `jsonl`, events include the standard fields:

- `ts`, `corr`, `component`, `level`, `action`, `result`, `rc`

Example:

```bash
koruenv --log-format jsonl env cursor cursor-main --shell bash
```
