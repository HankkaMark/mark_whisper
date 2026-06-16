# Whisper install — tries Python bootstrap (works when .ps1 scripts are blocked)
$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$Bootstrap = Join-Path $ProjectRoot "tools\bootstrap_install.py"
$FindScript = Join-Path $ProjectRoot "scripts\find_python.ps1"

Write-Host "Installing Whisper Assistant..." -ForegroundColor Cyan

function Invoke-Bootstrap {
    param([string]$PythonExe)
    & $PythonExe $Bootstrap
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# Prefer Python bootstrap (no signed-script policy issues)
$knownGood = @(
    "C:\Users\Default\AppData\Local\Koi\Python\WPy64-31290\python\python.exe"
)
if ($env:WHISPER_PYTHON -and (Test-Path $env:WHISPER_PYTHON)) {
    Invoke-Bootstrap $env:WHISPER_PYTHON
    exit 0
}
$pathFile = Join-Path $ProjectRoot ".python-path"
if (Test-Path $pathFile) {
    $p = (Get-Content $pathFile -First 1).Trim()
    if ($p -and (Test-Path $p)) {
        Invoke-Bootstrap $p
        exit 0
    }
}
foreach ($p in $knownGood) {
    if ($p -and (Test-Path $p)) {
        try {
            $null = & $p -c "import encodings" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Invoke-Bootstrap $p
                exit 0
            }
        } catch { }
    }
}

# Fallback: signed-policy-friendly cmd installer
$cmd = Join-Path $ProjectRoot "install.cmd"
if (Test-Path $cmd) {
    cmd /c "`"$cmd`""
    exit $LASTEXITCODE
}

# Last resort: find_python.ps1 (may fail on locked-down PCs)
if (Test-Path $FindScript) {
    try {
        . $FindScript
        $base = Find-WhisperPython -SavePath -ProjectRoot $ProjectRoot
        if ($base) { Invoke-Bootstrap $base; exit 0 }
    } catch {
        Write-Host "PowerShell helper blocked: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "No working Python found. Run install.cmd or set WHISPER_PYTHON." -ForegroundColor Red
exit 1
