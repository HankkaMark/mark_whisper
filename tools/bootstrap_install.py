"""Install Whisper using whatever working Python is on this PC (no PowerShell required)."""
from __future__ import annotations

import glob
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / ".venv"
PATH_FILE = PROJECT_ROOT / ".python-path"
MIN_VERSION = (3, 11)


def test_python(exe: str) -> bool:
    try:
        r = subprocess.run(
            [exe, "-c", "import encodings; import sys"],
            capture_output=True,
            timeout=30,
        )
        if r.returncode != 0:
            return False
        r2 = subprocess.run(
            [exe, "-c", "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,11) else 1)"],
            capture_output=True,
            timeout=30,
        )
        return r2.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def collect_candidates() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def add(path: str | None) -> None:
        if not path:
            return
        p = Path(path).resolve()
        if p.is_file() and str(p) not in seen:
            seen.add(str(p))
            out.append(str(p))

    if os.environ.get("WHISPER_PYTHON"):
        add(os.environ["WHISPER_PYTHON"])
    if PATH_FILE.is_file():
        add(PATH_FILE.read_text(encoding="utf-8").strip().splitlines()[0].strip())

    venv_py = VENV_DIR / "Scripts" / "python.exe"
    add(str(venv_py) if venv_py.is_file() else None)

    # py launcher
    try:
        listed = subprocess.run(
            ["py", "-0p"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        for line in (listed.stdout or "").splitlines():
            line = line.strip()
            if line.endswith("python.exe"):
                parts = line.split()
                add(parts[-1] if parts else None)
    except (OSError, subprocess.TimeoutExpired):
        pass

    patterns = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python3*\python.exe"),
        r"C:\Program Files\Python3*\python.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Koi\Python\*\python\python.exe"),
        r"C:\Users\Default\AppData\Local\Koi\Python\*\python\python.exe",
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Koi\Python\*\python\python.exe"),
    ]
    for pat in patterns:
        for match in glob.glob(pat):
            add(match)

    if sys.executable:
        add(sys.executable)

    return out


def find_python() -> str | None:
    for exe in collect_candidates():
        if test_python(exe):
            return exe
    return None


def venv_ok() -> bool:
    py = VENV_DIR / "Scripts" / "python.exe"
    return py.is_file() and test_python(str(py))


def run(cmd: list[str], check: bool = True, **kwargs) -> int:
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, **kwargs)
    if check and r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, cmd)
    return r.returncode


def main() -> int:
    print("Whisper bootstrap install")
    print("Project:", PROJECT_ROOT)

    base = find_python()
    if not base:
        print("\nERROR: No working Python 3.11+ found.", file=sys.stderr)
        print("Set WHISPER_PYTHON to a valid python.exe, or install Python:", file=sys.stderr)
        print("  winget install Python.Python.3.12", file=sys.stderr)
        return 1

    print("Using:", base)
    PATH_FILE.write_text(base + "\n", encoding="utf-8")

    if VENV_DIR.exists() and not venv_ok():
        print("Removing broken .venv ...")
        import shutil

        shutil.rmtree(VENV_DIR, ignore_errors=True)

    if not venv_ok():
        print("Creating virtual environment ...")
        run([base, "-m", "venv", str(VENV_DIR)])

    venv_python = str(VENV_DIR / "Scripts" / "python.exe")
    if not test_python(venv_python):
        print("ERROR: venv creation failed", file=sys.stderr)
        return 1

    pip_args = ["-m", "pip", "install", "--default-timeout", "120"]
    run([venv_python, *pip_args, "--upgrade", "pip"], check=False)

    req = PROJECT_ROOT / "requirements.txt"
    if req.is_file():
        run([venv_python, *pip_args, "-r", str(req)])
    else:
        run([venv_python, *pip_args, "-e", str(PROJECT_ROOT)])

    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    run(
        [venv_python, "-c", "from whisper.config import load_config; c=load_config(); print('Config:', c.data_dir)"],
        env=env,
    )

    whisper_home = Path.home() / ".whisper"
    whisper_home.mkdir(exist_ok=True)
    (whisper_home / "personas").mkdir(exist_ok=True)
    (whisper_home / "logs").mkdir(exist_ok=True)
    env_file = whisper_home / ".env"
    if not env_file.exists():
        env_file.write_text(
            "# Add your API keys\nOPENAI_API_KEY=sk-your-key-here\n",
            encoding="utf-8",
        )
        print("Created", env_file)

    print("\nDone. Run: run-whisper.cmd")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
