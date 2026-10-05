<#
.SYNOPSIS  Create/verify the product .venv and add python3.exe (needed by hooks and skills).
.EXAMPLE   powershell -ExecutionPolicy Bypass -File scripts\windows\setup-venv.ps1
#>
. (Join-Path $PSScriptRoot '_common.ps1')

if (-not (Test-Path $script:VenvPython)) {
    Write-Host 'Creating .venv ...'
    & python -m venv (Join-Path $script:ProductRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'python -m venv failed' }
}
$version = & $script:VenvPython -c "import sys;print('%d.%d' % sys.version_info[:2])"
$parts = $version.Split('.')
if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
    throw "Python $version found; 3.11 or newer is required."
}
# The venv launcher locates pyvenv.cfg next to itself, so a copy in Scripts\ works.
$py3 = Join-Path $script:VenvScripts 'python3.exe'
if (-not (Test-Path $py3)) { Copy-Item $script:VenvPython $py3 }
Write-Host "OK: Python $version, python3.exe present in .venv\Scripts"
Write-Host 'The core uses only the standard library; no pip install is required.'
