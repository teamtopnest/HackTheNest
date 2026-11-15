# Decoder tests, then the headset-stream tests. MongoDB tests stay off unless -Mongo.
# Usage, from the repo root:
#   .\backend\scripts\test.ps1
#   .\backend\scripts\test.ps1 -Mongo

param(
    [switch]$Mongo
)

. "$PSScriptRoot\_common.ps1"

Push-Location $RepoRoot
try {
    & $Python -m unittest tests.test_backend -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $Python -m pytest backend\tests\test_app.py backend\tests\test_device.py backend\tests\test_filter.py -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if ($Mongo) {
        & $Python -m pytest backend\tests\test_normalization.py backend\tests\test_api_sender.py backend\tests\test_mongo_integration.py -q
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
