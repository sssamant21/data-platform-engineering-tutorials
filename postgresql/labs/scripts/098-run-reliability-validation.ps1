# Chapter 098: Read-only PostgreSQL evidence collection (PowerShell 5.1+)
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$SqlPath,
  [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
try {
  if (-not (Test-Path -LiteralPath $SqlPath -PathType Leaf)) { throw "SQL file not found" }
  $psql = Get-Command psql -ErrorAction Stop
  $resolvedSql = (Resolve-Path -LiteralPath $SqlPath).Path
  New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
  $timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
  $output = Join-Path $OutputDirectory ("pg098-" + $timestamp + ".txt")
  # Timeouts applied before connecting. Do not overwrite existing PGOPTIONS.
  $oldOptions = $env:PGOPTIONS
  $env:PGOPTIONS = (($oldOptions + ' -c statement_timeout=15000 -c lock_timeout=3000').Trim())
  try {
    & $psql.Source -X -w -v ON_ERROR_STOP=1 -P pager=off -f $resolvedSql 2>&1 |
      Out-File -FilePath $output -Encoding UTF8
    $exitCode = $LASTEXITCODE
  } finally {
    $env:PGOPTIONS = $oldOptions
  }
  if ($exitCode -ne 0) { throw "psql failed with exit code $exitCode; inspect $output" }
  Write-Output "Evidence saved: $output"
  exit 0
} catch {
  Write-Error ("Reliability validation failed: " + $_.Exception.Message)
  exit 1
}
