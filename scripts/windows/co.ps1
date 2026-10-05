<#
.SYNOPSIS  Run the portable CLI from .venv with reduced-guarantee Windows writes enabled.
.EXAMPLE   scripts\windows\co.ps1 doctor --vault E:\vaults\my-wiki
.EXAMPLE   scripts\windows\co.ps1 init E:\vaults\my-wiki --generated-at 2026-10-05T00:00:00Z --operation-id init-reviewed
           (review the printed approved_plan_sha256, then repeat with --approved-plan-sha256 <hash> --apply)
#>
. (Join-Path $PSScriptRoot '_common.ps1')
Enter-OperatingEnv
& $script:VenvPython (Join-Path $script:ProductRoot 'scripts\claude-obsidian.py') @args
exit $LASTEXITCODE
