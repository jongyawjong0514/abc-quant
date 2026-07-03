param(
    [switch]$Strict
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = "python"
}

$ScriptArgs = @(
    (Join-Path $ProjectRoot "scripts\codex_loop_guard.py"),
    "--root",
    $ProjectRoot
)

if ($Strict) {
    $ScriptArgs += "--strict"
}

& $Python @ScriptArgs
exit $LASTEXITCODE
