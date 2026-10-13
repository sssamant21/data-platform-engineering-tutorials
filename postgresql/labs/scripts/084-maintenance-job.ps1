# Chapter 084 — Lab-only maintenance runner. No embedded secrets.
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Database,
  [switch]$Execute,
  [switch]$DryRun,
  [string]$HostName = "localhost",
  [int]$Port = 5432,
  [string]$User = "postgres"
)
$ErrorActionPreference = "Stop"
if ($Database -ne "ch084_lab") { throw "Only disposable ch084_lab is permitted." }
if ($Execute -and $DryRun) { throw "Choose Execute or DryRun, not both." }
$start = (Get-Date).ToUniversalTime()
$lockPath = Join-Path ([IO.Path]::GetTempPath()) "ch084-maintenance-exclusive.lock"
$lock = $null
try {
  # Exclusive file handle: prevents overlap only on this host.
  $lock = [IO.File]::Open($lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
  Write-Output ("START_UTC=" + $start.ToString("o"))
  Write-Output ("DATABASE=" + $Database)
  if (-not $Execute) {
    Write-Output "DRY_RUN: no SQL executed."
    exit 0
  }
  $sql = "SET lock_timeout='3s'; SET statement_timeout='120s'; SELECT pg_is_in_recovery();"
  $preflight = & psql -X -w -h $HostName -p $Port -U $User -d $Database -v ON_ERROR_STOP=1 -Atc $sql
  if ($LASTEXITCODE -ne 0) { throw "Preflight failed with psql exit code $LASTEXITCODE" }
  if (($preflight | Select-Object -Last 1).Trim() -ne "f") { throw "Refusing write maintenance on standby." }
  # Apply session timeouts through PGOPTIONS; VACUUM must be the sole -c command.
  $previousPgOptions = $env:PGOPTIONS
  $env:PGOPTIONS = "-c lock_timeout=3s -c statement_timeout=120s"
  try {
    & psql -X -w -h $HostName -p $Port -U $User -d $Database -v ON_ERROR_STOP=1 -c "VACUUM (ANALYZE) public.ch084_events;"
    $vacuumExitCode = $LASTEXITCODE
  }
  finally { $env:PGOPTIONS = $previousPgOptions }
  if ($vacuumExitCode -ne 0) { throw "Maintenance failed with psql exit code $vacuumExitCode" }
  Write-Output "RESULT=SUCCESS"
}
catch {
  Write-Error ("RESULT=FAILED " + $_.Exception.Message)
  exit 1
}
finally {
  if ($null -ne $lock) { $lock.Dispose() }
  Write-Output ("END_UTC=" + (Get-Date).ToUniversalTime().ToString("o"))
}
