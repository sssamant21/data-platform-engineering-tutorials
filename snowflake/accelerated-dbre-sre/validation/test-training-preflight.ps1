# Synthetic integration tests for V03 Windows preflight (NO REAL SNOWFLAKE).
# A PowerShell *function* named snow intercepts every attempted CLI call.
# This file must be run only via isolated CI, not an account with credentials.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$preflight = Join-Path $PSScriptRoot "run-training-preflight.ps1"
if (-not (Test-Path -LiteralPath $preflight -PathType Leaf)) {
    throw "Launcher not found"
}
$global:MockCalls = 0
$global:MockSqlRuns = 0
$global:MockFailure = $false
$global:MockResult = @'
[{
  "ACCOUNT_LOCATOR":"TRAINING001",
  "ORGANIZATION_NAME":"TESTORG",
  "REGION_NAME":"AWS_US_WEST_2",
  "ROLE_ALIAS":"DBRE_TRAINING",
  "WAREHOUSE_ALIAS":"TRAINING_XS",
  "DATABASE_ALIAS":"DBRE_SRE_LAB",
  "SCHEMA_ALIAS":"TRAINING_SCRATCH"
}]
'@
function global:snow {
    $global:MockCalls++
    $argv = @($args)
    if ($argv -contains "--filename") {
        $global:MockSqlRuns++
        $global:LASTEXITCODE = 0
        return "MOCK_SQL_ONLY"
    }
    if ($global:MockFailure) {
        $global:LASTEXITCODE = 5
        return "MOCK_ERROR_DO_NOT_ECHO"
    }
    $global:LASTEXITCODE = 0
    return $global:MockResult
}
# Ensure the mock, not the real external snow command, is resolved.
if ((Get-Command snow).CommandType -ne "Function") {
    throw "Refusing to test: Snowflake mock was not installed"
}
$params = @{
    Connection = "MOCK_NONPROD_ONLY"
    ExpectedAccountLocator = "TRAINING001"
    ExpectedOrganization = "TESTORG"
    ExpectedRegion = "AWS_US_WEST_2"
    ExpectedRole = "DBRE_TRAINING"
    ExpectedWarehouse = "TRAINING_XS"
    ExpectedDatabase = "DBRE_SRE_LAB"
    ExpectedSchema = "TRAINING_SCRATCH"
    ApprovedNonProductionAccount = $true
}
function ShouldReject([hashtable]$override, [string]$name) {
    $before = $global:MockSqlRuns
    $p = $params.Clone()
    foreach ($entry in $override.GetEnumerator()) {
        $p[$entry.Key] = $entry.Value
    }
    try {
        $null = & $preflight @p -Mode Preflight 2>&1
    }
    catch {
        if ($global:MockSqlRuns -ne $before) {
            throw "FAIL: $name triggered a lesson execution"
        }
        Write-Output "PASS: $name blocked"
        return
    }
    throw "FAIL: $name unexpectedly permitted"
}
$pass = & $preflight @params -Mode Preflight
if (($pass -join " ") -notmatch "V03 context preflight PASS" -or $global:MockSqlRuns -ne 0) {
    throw "Correct nonproduction preflight failed or ran a lesson"
}
Write-Output "PASS: matching training context; no lesson SQL"
ShouldReject @{ ExpectedAccountLocator = "WRONG_ACCOUNT" } "wrong account locator"
ShouldReject @{ ExpectedOrganization = "OTHER_ORG" } "wrong organization"
ShouldReject @{ ExpectedRegion = "WRONG_REGION" } "wrong region"
ShouldReject @{ ExpectedRole = "ACCOUNTADMIN" } "administrator role"
ShouldReject @{ ApprovedNonProductionAccount = $false } "missing owner attestation"
# Check that L1/L2 cannot proceed even with a valid mock connection
# unless explicit prerequisites are supplied.
try {
    $null = & $preflight @params -Mode Level1 -ApprovalReference "TRAINING_APPROVAL" 2>&1
    throw "FAIL: L1 started without verified scratch schema"
}
catch {
    if ($_.Exception.Message -like "FAIL:*") { throw }
    if ($global:MockSqlRuns -ne 0) { throw "FAIL: L1 invoked SQL" }
    Write-Output "PASS: Level1 blocked without empty scratch attestation"
}
try {
    $null = & $preflight @params -Mode Level2 -ApprovalReference "TRAINING_APPROVAL" 2>&1
    throw "FAIL: L2 started without independently accepted L1"
}
catch {
    if ($_.Exception.Message -like "FAIL:*") { throw }
    if ($global:MockSqlRuns -ne 0) { throw "FAIL: L2 invoked SQL" }
    Write-Output "PASS: Level2 blocked without Level1 acceptance"
}
$global:MockFailure = $true
ShouldReject @{} "connection execution failure"
Write-Output "V03 PowerShell mock integration tests PASS (zero live Snowflake calls)"
