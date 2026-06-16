# Find a working Python 3.11+ on this machine.
# Usage:
#   . .\scripts\find_python.ps1
#   $py = Find-WhisperPython
#   & $py -c "print('ok')"

function Test-WhisperPython {
    param([string]$PythonExe)
    if (-not $PythonExe -or -not (Test-Path -LiteralPath $PythonExe)) {
        return $false
    }
    try {
        $null = & $PythonExe -c "import encodings, sys; assert sys.version_info >= (3, 11)" 2>&1
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Get-WhisperPythonCandidates {
  $candidates = [System.Collections.Generic.List[string]]::new()

  $add = {
    param([string]$Path)
    if ($Path -and (Test-Path -LiteralPath $Path) -and ($candidates -notcontains $Path)) {
      [void]$candidates.Add($Path)
    }
  }

  # 1) User override: env var or project file
  if ($env:WHISPER_PYTHON) { & $add $env:WHISPER_PYTHON }
  $projectRoot = if ($PSScriptRoot -match 'scripts$') {
    Split-Path $PSScriptRoot -Parent
  } else {
    $PSScriptRoot
  }
  $pathFile = Join-Path $projectRoot ".python-path"
  if (Test-Path $pathFile) {
    $line = (Get-Content $pathFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($line) { & $add $line }
  }

  # 2) Existing venv (if already installed)
  & $add (Join-Path $projectRoot ".venv\Scripts\python.exe")

  # 3) py launcher — all registered installs
  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($pyLauncher) {
    try {
      $list = & py -0p 2>&1
      foreach ($row in $list) {
        if ($row -match '(.:\\.*python\.exe)\s*$') {
          & $add $Matches[1].Trim()
        }
      }
    } catch { }
    & $add (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe")
  }

  # 4) Common install locations
  $patterns = @(
    "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python3*\python3.exe",
    "C:\Program Files\Python3*\python.exe",
    "C:\Program Files (x86)\Python3*\python.exe",
    "$env:LOCALAPPDATA\Koi\Python\*\python\python.exe",
    "C:\Users\Default\AppData\Local\Koi\Python\*\python\python.exe",
    "$env:USERPROFILE\AppData\Local\Koi\Python\*\python\python.exe"
  )
  foreach ($pat in $patterns) {
    Get-ChildItem -Path $pat -ErrorAction SilentlyContinue | ForEach-Object {
      & $add $_.FullName
    }
  }

  # 5) PATH (last — often Windows Store stub)
  foreach ($name in @("python", "python3")) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notmatch 'WindowsApps') {
      & $add $cmd.Source
    }
  }

  return $candidates
}

function Find-WhisperPython {
  param(
    [switch]$SavePath,
    [string]$ProjectRoot = (Split-Path $PSScriptRoot -Parent)
  )

  foreach ($exe in (Get-WhisperPythonCandidates)) {
    if (Test-WhisperPython $exe) {
      if ($SavePath) {
        $out = Join-Path $ProjectRoot ".python-path"
        Set-Content -Path $out -Value $exe -Encoding UTF8 -NoNewline
      }
      return $exe
    }
  }
  return $null
}

# When dot-sourced, export functions; when run directly, print path or exit 1
if ($MyInvocation.InvocationName -ne '.') {
  $found = Find-WhisperPython -SavePath
  if ($found) {
    Write-Output $found
    exit 0
  }
  Write-Error "No working Python 3.11+ found. Run install.ps1 or set WHISPER_PYTHON to a valid python.exe"
  exit 1
}
