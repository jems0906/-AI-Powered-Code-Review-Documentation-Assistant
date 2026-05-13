param(
    [string]$DbService = "db",
    [string]$DbUser = "codereview",
    [string]$DbName = "codereview",
    [switch]$Reset
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$seedFiles = @(
    "seed_demo_data.sql"
)

Push-Location $repoRoot
try {
    Write-Host "Checking Docker Compose services..."
    docker compose ps | Out-Null

    if ($Reset) {
        Write-Host "Resetting review data tables..."
        $resetSql = @"
TRUNCATE TABLE review_comments, reviews RESTART IDENTITY CASCADE;
"@

        $resetSql | docker compose exec -T $DbService psql -U $DbUser -d $DbName
    }

    foreach ($seedFile in $seedFiles) {
        $seedPath = Join-Path $repoRoot $seedFile
        if (-not (Test-Path $seedPath)) {
            throw "Seed file not found: $seedPath"
        }

        Write-Host "Applying $seedFile..."
        Get-Content -Raw $seedPath | docker compose exec -T $DbService psql -U $DbUser -d $DbName
    }

    Write-Host "Backfilling generated test artifacts for demo rows..."
    $testsBackfillSql = @'
UPDATE reviews
SET generated_tests =
    CASE LOWER(COALESCE(extra_meta->>'language', ''))
        WHEN 'python' THEN E'```python\n# Auto-generated regression test\ndef test_behavior_regression_guard():\n    assert True\n```'
        WHEN 'typescript' THEN E'```typescript\ndescribe("behaviorRegressionGuard", () => {\n  it("preserves existing behavior", () => {\n    expect(true).toBe(true)\n  })\n})\n```'
        WHEN 'javascript' THEN E'```javascript\ndescribe("behaviorRegressionGuard", () => {\n  it("preserves existing behavior", () => {\n    expect(true).toBe(true)\n  })\n})\n```'
        WHEN 'java' THEN E'```java\nimport static org.junit.jupiter.api.Assertions.assertTrue;\nimport org.junit.jupiter.api.Test;\n\nclass RegressionTest {\n    @Test\n    void behaviorRegressionGuardShouldPreserveBehavior() {\n        assertTrue(true);\n    }\n}\n```'
        WHEN 'go' THEN E'```go\npackage regression\n\nimport "testing"\n\nfunc TestBehaviorRegressionGuard(t *testing.T) {\n}\n```'
        WHEN 'ruby' THEN E'```ruby\nRSpec.describe "regression guard" do\n  it "preserves existing behavior" do\n    expect(true).to eq(true)\n  end\nend\n```'
        WHEN 'csharp' THEN E'```csharp\nusing Xunit;\n\npublic class RegressionTests\n{\n    [Fact]\n    public void BehaviorRegressionGuard_PreservesBehavior()\n    {\n        Assert.True(true);\n    }\n}\n```'
        ELSE E'```text\nAdd project-specific regression tests for changed functions and edge cases.\n```'
    END
WHERE id::text LIKE '11111111-%'
    OR id::text LIKE '22222222-%'
    OR id::text LIKE '33333333-%';
'@
    $testsBackfillSql | docker compose exec -T $DbService psql -U $DbUser -d $DbName

    Write-Host "`nVerifying seeded data..."
    $metrics = Invoke-WebRequest -UseBasicParsing "http://localhost:8000/api/metrics/summary" | Select-Object -ExpandProperty Content
    $reviews = Invoke-WebRequest -UseBasicParsing "http://localhost:8000/api/reviews/?limit=1" | Select-Object -ExpandProperty Content

    Write-Host "Metrics:"
    Write-Host $metrics
    Write-Host "`nReviews sample:"
    Write-Host $reviews
    Write-Host "`nDone. Open http://localhost:3000/reviews"
}
finally {
    Pop-Location
}
