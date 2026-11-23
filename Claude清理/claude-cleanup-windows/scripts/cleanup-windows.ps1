[CmdletBinding()]
param([switch]$Audit, [string]$Restore)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Run this on native Windows, not WSL/macOS.' }
if ($Audit -and $Restore) { throw 'Choose Audit or Restore, not both.' }
$runner = $null
$prefixArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    $runner = (Get-Command py).Source
    $prefixArgs = @('-3')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $runner = (Get-Command python).Source
}
if (-not $runner) { throw 'Python 3.10+ is required. Install it from python.org or use your existing Python.' }
& $runner @prefixArgs -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required.' }
$scriptPath = Join-Path $PSScriptRoot 'cleanup_windows.py'
$scriptArgs = @()
if ($Audit) { $scriptArgs = @('--audit') }
if ($Restore) { $scriptArgs = @('--restore', $Restore) }
& $runner @prefixArgs $scriptPath @scriptArgs
exit $LASTEXITCODE
