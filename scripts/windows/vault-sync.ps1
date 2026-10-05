<#
.SYNOPSIS  Lint a vault, show pending changes, and (only after confirmation) commit and push.
.EXAMPLE   scripts\windows\vault-sync.ps1 -Vault E:\vaults\my-wiki -Message "ingest: article X"
Checkpointing is unavailable on native Windows, so plain git is the history/rollback tool.
#>
param(
    [Parameter(Mandatory = $true)][string]$Vault,
    [Parameter(Mandatory = $true)][string]$Message,
    [switch]$Push
)
. (Join-Path $PSScriptRoot '_common.ps1')
Enter-OperatingEnv
$Vault = (Resolve-Path $Vault).Path

$lint = & $script:VenvPython (Join-Path $script:ProductRoot 'scripts\claude-obsidian.py') lint --vault $Vault | ConvertFrom-Json
$issues = $lint.summary.issues_found
Write-Host "Lint issues: $issues"
if ($issues -gt 0) { Write-Warning 'Fix or acknowledge lint findings before committing.' }

& git -C $Vault status --short
$answer = Read-Host 'Commit all changes above? (y/N)'
if ($answer -ne 'y') { Write-Host 'Aborted.'; exit 1 }
& git -C $Vault add -A
& git -C $Vault commit -m $Message
if ($Push) {
    $answer = Read-Host 'Push to origin? (y/N)'
    if ($answer -eq 'y') { & git -C $Vault push }
}
