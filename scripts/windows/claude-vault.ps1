<#
.SYNOPSIS  Start Claude Code inside a vault with this product loaded as a local plugin.
.EXAMPLE   scripts\windows\claude-vault.ps1 -Vault E:\vaults\my-wiki
#>
param([Parameter(Mandatory = $true)][string]$Vault)
. (Join-Path $PSScriptRoot '_common.ps1')
Enter-OperatingEnv
$Vault = (Resolve-Path $Vault).Path
if (-not (Test-Path (Join-Path $Vault '.claude-obsidian.json'))) {
    throw "$Vault is not a claude-obsidian vault (.claude-obsidian.json missing)."
}
if ($Vault.StartsWith($script:ProductRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'The vault must live outside the product checkout.'
}
$env:CLAUDE_OBSIDIAN_VAULT = $Vault
Set-Location $Vault
& claude --plugin-dir $script:ProductRoot
