<#
.SYNOPSIS  Run every tests\test_*.py with .venv Python (Windows replacement for `make test`).
Known: POSIX-only suites (symlink privilege, bash, fcntl) fail on native Windows by design.
Use -Reduced to run with the opt-in write mode enabled.
#>
param([switch]$Reduced)
. (Join-Path $PSScriptRoot '_common.ps1')
Assert-Venv
if ($Reduced) { $env:CLAUDE_OBSIDIAN_ALLOW_REDUCED_WRITES = '1' } else { Remove-Item Env:CLAUDE_OBSIDIAN_ALLOW_REDUCED_WRITES -ErrorAction SilentlyContinue }
$failed = @()
foreach ($t in Get-ChildItem (Join-Path $script:ProductRoot 'tests') -Filter 'test_*.py') {
    & $script:VenvPython $t.FullName *> $null
    $status = if ($LASTEXITCODE -eq 0) { 'PASS' } else { $failed += $t.Name; 'FAIL' }
    '{0}  {1}' -f $status, $t.Name
}
if ($failed.Count) { Write-Host "$($failed.Count) suite(s) failed"; exit 1 }
