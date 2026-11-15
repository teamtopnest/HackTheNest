# Fit the LDA on every flash in the given MAT files and save it.
# Usage, from the repo root:
#   .\backend\scripts\train.ps1
#   .\backend\scripts\train.ps1 -Output D:\models\s1.joblib backend\resources\unicorn-bi\S1.mat

param(
    [string]$Output,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Recordings
)

. "$PSScriptRoot\_common.ps1"

if (-not $Output) {
    $Output = Join-Path $BackendRoot "model.joblib"
}
if (-not $Recordings -or $Recordings.Count -eq 0) {
    if (-not (Test-Path -LiteralPath $DataDir)) {
        throw "No MAT directory at $DataDir. Pass recording paths to this script."
    }
    $Recordings = @(Get-ChildItem -LiteralPath $DataDir -Filter "S*.mat" | Sort-Object Name | ForEach-Object FullName)
}
if ($Recordings.Count -eq 0) {
    throw "No S*.mat files in $DataDir."
}

Push-Location $RepoRoot
try {
    & $Python -m backend.decoder.live_decoder --train --output $Output @Recordings
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
