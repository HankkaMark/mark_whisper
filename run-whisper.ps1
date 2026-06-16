# Start Whisper — minimal launcher (no installs, no script scanning)
$ProjectRoot = $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Error "Missing .venv. Run install.cmd once (offline-friendly), then use run-whisper.cmd"
    exit 1
}

Set-Location $ProjectRoot
$env:PYTHONPATH = $ProjectRoot
& $Python -m whisper
