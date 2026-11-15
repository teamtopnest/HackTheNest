# Unicorn Hybrid Black WebSocket on http://127.0.0.1:8000
# Stop the ingestion API first. It uses the same port.
# Usage, from the repo root:
#   .\backend\scripts\stream.ps1

. "$PSScriptRoot\_common.ps1"

Push-Location $RepoRoot
try {
    & $Python backend\run.py
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
