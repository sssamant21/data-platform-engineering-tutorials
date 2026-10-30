# Snowflake DBRE/SRE V03: interactive nonproduction preflight and manual opt-in.
# Windows PowerShell 5.1+ / PowerShell 7+. Does NOT store credentials or logs.
# Preflight is read-only; no Snowflake SQL runs unless a configured connection exists.
# A TEST ACCOUNT IS MANDATORY. Never use production or protected customer data.
# --local-only blocks remote !source/!load directives; it is NOT an offline mode.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Connection,
    [Parameter(Mandatory = $true)][string]$ExpectedAccountLocator,
    [Parameter(Mandatory = $true)][string]$ExpectedRole,
    [Parameter(Mandatory = $true)][string]$ExpectedWarehouse,
    [Parameter(Mandatory = $true)][string]$ExpectedDatabase,
    [Parameter(Mandatory = $true)][string]$ExpectedSchema,
    [ValidateSet("Preflight", "Level1", "Level2")][string]$Mode = "Preflight",
    [ValidateSet("TRAINING", "SANDBOX", "STAGING")][string]$EnvironmentClass = "TRAINING",
    [switch]$ApprovedNonProductionAccount,
    [switch]$ScratchSchemaVerifiedEmpty,
    [switch]$Level1Accepted,
    [string]$ApprovalReference = ""
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Deny([string]$message) {
    throw ("V03 BLOCKED: " + $message)
}
if (-not $ApprovedNonProductionAccount) {
    Deny "Account owner must confirm that the target is a nonproduction training, sandbox or staging account."
}
if ($ExpectedRole.ToUpperInvariant() -in @("ACCOUNTADMIN", "SECURITYADMIN", "USERADMIN", "ORGADMIN", "SYSADMIN", "GLOBALORGADMIN")) {
    Deny "An administrative role is prohibited for these training smoke tests."
}
if (-not (Get-Command snow -ErrorAction SilentlyContinue)) {
    Deny "Snowflake CLI ('snow') is not installed or not on PATH."
}
if ($Mode -ne "Preflight") {
    if ([string]::IsNullOrWhiteSpace($ApprovalReference) -or $ApprovalReference.Length -lt 3) {
        Deny "An approved test/change reference is required before executing a lesson."
    }
}
if ($Mode -eq "Level1" -and -not $ScratchSchemaVerifiedEmpty) {
    Deny "A training owner must confirm the scratch schema is empty and has no naming conflicts."
}
if ($Mode -eq "Level2" -and -not $Level1Accepted) {
    Deny "An independent reviewer must first accept the executed Level 1 evidence."
}
# One SELECT in the configured connection. Parse output but do not print actual identifiers.
$sql = @"
SELECT CURRENT_ACCOUNT() AS ACCOUNT_LOCATOR,
       CURRENT_ROLE() AS ROLE_ALIAS,
       CURRENT_WAREHOUSE() AS WAREHOUSE_ALIAS,
       CURRENT_DATABASE() AS DATABASE_ALIAS,
       CURRENT_SCHEMA() AS SCHEMA_ALIAS
"@
try {
    $output = & snow sql --connection $Connection --local-only --enhanced-exit-codes --format JSON --query $sql 2>&1
    if ($LASTEXITCODE -ne 0) {
        Deny "Snowflake CLI preflight query failed; verify configuration and authentication privately."
    }
    $parsed = $output | Out-String | ConvertFrom-Json
    $rows = @($parsed)
    if ($rows.Count -ne 1) {
        Deny "Expected exactly one JSON row in the Snowflake preflight result."
    }
    $context = $rows[0]
    # Case-sensitive matches are intentionally conservative (fail closed).
    $checks = @{
        ACCOUNT_LOCATOR = $ExpectedAccountLocator
        ROLE_ALIAS = $ExpectedRole
        WAREHOUSE_ALIAS = $ExpectedWarehouse
        DATABASE_ALIAS = $ExpectedDatabase
        SCHEMA_ALIAS = $ExpectedSchema
    }
    foreach ($field in $checks.Keys) {
        $prop = $context.PSObject.Properties[$field]
        if ($null -eq $prop -or $null -eq $prop.Value) {
            Deny "Snowflake preflight returned an unexpected or NULL context field."
        }
        if ([string]$prop.Value -cne [string]$checks[$field]) {
            Deny "Connected Snowflake context does not match approved expectations (field: $field)."
        }
    }
}
catch {
    # Do not emit the underlying connector/SQL error: it can contain private context.
    Deny "Snowflake connection or context verification failed. Check account/role locally."
}
Write-Output ("V03 context preflight PASS — " + $EnvironmentClass + " classification was operator-attested.")
if ($Mode -eq "Preflight") {
    Write-Output "Read-only check finished. No instructional SQL or DDL was executed."
    exit 0
}
if ($Mode -eq "Level1") { $filename = "runtime/level-01-smoke.sql" }
else { $filename = "runtime/level-02-smoke.sql" }
$scriptPath = Join-Path -Path $PSScriptRoot -ChildPath $filename
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
    Deny "Required version-controlled SQL file not found locally."
}
Write-Output "The lesson SQL runs against the *configured live training account*."
Write-Output "The preflight used a separate connection; confirm the connection configuration did not change."
Write-Output "Never redirect raw query results, credentials or query text to a shared log."
$expectedPhrase = "RUN " + $Mode.ToUpperInvariant() + " IN TRAINING"
$answer = Read-Host ("Type exactly '" + $expectedPhrase + "' to proceed")
if ($answer -cne $expectedPhrase) {
    Deny "Interactive approval phrase not supplied."
}
# One CLI call executes all SQL statements in the selected file on a single connection.
# No automatic L2 execution: run only after Level 1 reviewer acceptance.
& snow sql --connection $Connection --local-only --enhanced-exit-codes --filename $scriptPath
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Deny ("Snowflake CLI lesson ended with an error code " + $exitCode + ". No V03 PASS may be claimed.")
}
Write-Output "SQL file completed; capture and verify query IDs/results in secure evidence store."
Write-Output "Execution is NOT V03 acceptance until independently reviewed."
