# Parse-only CI validation for the V03 PowerShell launcher.
# DO NOT import or invoke run-training-preflight.ps1 here: that script can access Snowflake.
$ErrorActionPreference = "Stop"
$target = Join-Path -Path $PSScriptRoot -ChildPath "run-training-preflight.ps1"
if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
    throw "PowerShell launcher is absent."
}
$tokens = $null
$parseErrors = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile(
    $target, [ref]$tokens, [ref]$parseErrors
)
if ($null -ne $parseErrors -and $parseErrors.Count -gt 0) {
    foreach ($item in $parseErrors) {
        Write-Error ("PowerShell syntax error at line " +
            $item.Extent.StartLineNumber + ": " + $item.ErrorId)
    }
    throw "V03 preflight script failed the static PowerShell syntax gate."
}
Write-Output "V03 PowerShell preflight parser PASS (no Snowflake execution)"
