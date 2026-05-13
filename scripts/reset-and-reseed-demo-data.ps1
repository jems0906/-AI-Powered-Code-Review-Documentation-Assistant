param(
    [string]$DbService = "db",
    [string]$DbUser = "codereview",
    [string]$DbName = "codereview"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$reseedScript = Join-Path $PSScriptRoot "reseed-demo-data.ps1"

if (-not (Test-Path $reseedScript)) {
    throw "Missing reseed script: $reseedScript"
}

Push-Location $repoRoot
try {
    Write-Host "Checking Docker Compose services..."
    docker compose ps | Out-Null

    Write-Host "Resetting review data tables..."
    $resetSql = @"
TRUNCATE TABLE review_comments, reviews RESTART IDENTITY CASCADE;
"@

    $resetSql | docker compose exec -T $DbService psql -U $DbUser -d $DbName

    Write-Host "Running reseed script..."
    & $reseedScript -DbService $DbService -DbUser $DbUser -DbName $DbName
}
finally {
    Pop-Location
}
