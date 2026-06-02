param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$ArgsList
)

if (-not (Get-Command koruenv -ErrorAction SilentlyContinue)) {
  Write-Error "koruenv command not found. Install package first: pip install -e ./packages/koruenv"
  exit 1
}

& koruenv @ArgsList
exit $LASTEXITCODE
