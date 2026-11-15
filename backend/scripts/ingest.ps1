# MAT ingestion API on http://127.0.0.1:8000
# Requires backend\.env. Stop the headset WebSocket first. It uses the same port.
# Usage, from the repo root:
#   .\backend\scripts\ingest.ps1

. "$PSScriptRoot\_common.ps1"

$envFile = Join-Path $BackendRoot ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Error "Copy backend\.env.example to backend\.env and fill in MONGODB_URI, EEG_API_TOKEN, and EEG_OWNER_ID."
    exit 1
}

Push-Location $RepoRoot
try {
    & $Python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
