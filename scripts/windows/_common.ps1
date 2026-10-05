# Shared helpers for the native-Windows operating layer (ASCII only: PS 5.1 safe).
$ErrorActionPreference = 'Stop'
$script:ProductRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script:VenvScripts = Join-Path $script:ProductRoot '.venv\Scripts'
$script:VenvPython  = Join-Path $script:VenvScripts 'python.exe'

function Assert-Venv {
    if (-not (Test-Path $script:VenvPython)) {
        throw "Missing $script:VenvPython. Run scripts\windows\setup-venv.ps1 first."
    }
}

function Enter-OperatingEnv {
    # Opt-in reduced-guarantee writes + venv first on PATH (hooks spawn 'python3').
    Assert-Venv
    $env:CLAUDE_OBSIDIAN_ALLOW_REDUCED_WRITES = '1'
    if (($env:PATH -split ';')[0] -ne $script:VenvScripts) {
        $env:PATH = "$script:VenvScripts;$env:PATH"
    }
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PYTHONUTF8 = '1'   # retrieve.py prints non-cp949 characters
}
