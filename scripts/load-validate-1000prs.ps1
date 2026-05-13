param(
    [string]$DbService = "db",
    [string]$DbUser = "codereview",
    [string]$DbName = "codereview",
    [string]$RepoFullName = "loadtest/acme-scale",
    [int]$ReviewCount = 1000,
    [int]$Samples = 15,
    [switch]$Cleanup
)

$ErrorActionPreference = "Stop"

function Invoke-ApiTimed {
    param([string]$Url)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $null = Invoke-WebRequest -UseBasicParsing $Url
    $sw.Stop()
    return [math]::Round($sw.Elapsed.TotalMilliseconds, 2)
}

function Get-Percentile {
    param([double[]]$Values, [double]$Percentile)
    if (-not $Values -or $Values.Count -eq 0) { return 0 }
    $sorted = $Values | Sort-Object
    $index = [math]::Ceiling(($Percentile / 100.0) * $sorted.Count) - 1
    if ($index -lt 0) { $index = 0 }
    if ($index -ge $sorted.Count) { $index = $sorted.Count - 1 }
    return $sorted[$index]
}

$seedSql = @"
INSERT INTO reviews (
  id,
  repo_full_name,
  pr_number,
  pr_title,
  pr_author,
  status,
  review_profile,
  quality_score,
  comment_count,
  accepted_count,
  rejected_count,
  summary,
  generated_docs,
  generated_tests,
  ai_provider,
  created_at,
  completed_at
)
SELECT
  ('99999999-9999-9999-9999-' || LPAD(gs::text, 12, '0'))::uuid,
  '$RepoFullName',
  gs,
  'Load test PR #' || gs,
  'engineer.' || ((gs % 30) + 1)::text,
  'completed'::reviewstatus,
  CASE WHEN gs % 3 = 0 THEN 'pedantic' WHEN gs % 3 = 1 THEN 'balanced' ELSE 'relaxed' END,
  6 + ((gs % 40) / 10.0),
  3,
  (gs % 3),
  ((gs + 1) % 3),
  'Synthetic load validation review row.',
  '## Load Test Doc\nSynthetic row for scalability checks.',
  '```python\ndef test_load_validation_guard():\n    assert True\n```',
  CASE WHEN gs % 2 = 0 THEN 'openai' ELSE 'anthropic' END,
  NOW() - ((gs % 30) || ' days')::interval,
  NOW() - ((gs % 30) || ' days')::interval + INTERVAL '5 minutes'
FROM generate_series(1, $ReviewCount) AS gs
ON CONFLICT (id) DO NOTHING;
"@

$cleanupSql = @"
DELETE FROM review_comments
WHERE review_id IN (
  SELECT id FROM reviews WHERE repo_full_name = '$RepoFullName'
);

DELETE FROM reviews WHERE repo_full_name = '$RepoFullName';
"@

Write-Host "Ensuring services are running..."
docker compose up -d db backend | Out-Null

Write-Host "Seeding $ReviewCount synthetic reviews for $RepoFullName ..."
$seedSql | docker compose exec -T $DbService psql -U $DbUser -d $DbName | Out-Null

$timings = @()
$url = "http://localhost:8000/api/reviews/?repo_full_name=$RepoFullName&limit=100"
Write-Host "Running $Samples API samples on $url ..."
for ($i = 1; $i -le $Samples; $i++) {
    $timings += Invoke-ApiTimed -Url $url
}

$p50 = Get-Percentile -Values $timings -Percentile 50
$p95 = Get-Percentile -Values $timings -Percentile 95
$avg = [math]::Round((($timings | Measure-Object -Average).Average), 2)

Write-Host "Load validation summary"
Write-Host "  Samples: $Samples"
Write-Host "  Avg ms : $avg"
Write-Host "  P50 ms : $p50"
Write-Host "  P95 ms : $p95"

if ($Cleanup) {
    Write-Host "Cleaning up synthetic load data ..."
    $cleanupSql | docker compose exec -T $DbService psql -U $DbUser -d $DbName | Out-Null
    Write-Host "Cleanup complete."
}
