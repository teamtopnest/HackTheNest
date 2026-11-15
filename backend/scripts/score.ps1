# Score S1.mat-S5.mat, or the MAT paths you pass, with leave-one-character-out AUC.
# Usage, from the repo root:
#   .\backend\scripts\score.ps1
#   .\backend\scripts\score.ps1 backend\resources\unicorn-bi\S1.mat

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Recordings
)

. "$PSScriptRoot\_common.ps1"

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
    & $Python -m backend.decoder.live_decoder @Recordings
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
