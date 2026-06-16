# Whisper — Global Voice Dictate & Edit (Windows)

A background tray app that lets you dictate and edit text in any application using your voice, with switchable personas (work, student, casual).

## Features

- **Dictate** — Hold `Ctrl+Shift+Space`, speak, release → polished text pasted at cursor
- **Edit selection** — Select text, hold `Ctrl+Shift+E`, speak an instruction, release → selection replaced
- **Personas** — Work / Student / Casual / Default tones; switch from tray or `Ctrl+Shift+P`
- **Learn preferences** — Hold `Ctrl+Shift+R` and say what to remember; save edits as examples from tray
- **Configurable hotkeys** — Edit `%USERPROFILE%\.whisper\config.yaml` (no code changes)

## Requirements

- Windows 10/11
- Python 3.11+
- Microphone
- **OpenAI API key** (required for speech-to-text via Whisper API)
- **OpenAI and/or Anthropic API key** for text polish and edits

## Quick start

```powershell
cd whisper
.\install.ps1
```

**Auto Python detection:** `install.ps1` scans your PC for a working Python 3.11+ (tests `import encodings`). It will use, in order:

1. `WHISPER_PYTHON` environment variable
2. `.python-path` file in the project folder (one line: full path to `python.exe`)
3. An existing working `.venv`
4. `py` launcher registrations, WinPython/Koi, `Program Files`, etc.

On this machine, `C:\Program Files\Python312` is **broken** (missing `Lib\encodings`). A working copy was found at WinPython:

`C:\Users\Default\AppData\Local\Koi\Python\WPy64-31290\python\python.exe`

After install, the chosen path is saved to `.python-path`.

1. Edit `%USERPROFILE%\.whisper\.env` and set `OPENAI_API_KEY=sk-...`
2. Optionally set `ANTHROPIC_API_KEY` and set `providers.llm: anthropic` in config
3. Run:

```powershell
.\run-whisper.ps1
```

Or use the **Whisper** shortcut in the Start Menu.

**On company-managed PCs (McKinsey / firewall):** double-click **`START-whisper.vbs`** — it does **not** launch `cmd.exe` (often blocked as unapproved software). Avoid `.cmd` / `.bat` / PowerShell if IT flags them. Corporate safe mode is on by default (tray menu only, no global hotkeys, no simulated Ctrl+V).

See [`docs/CURSOR-global-setup.md`](docs/CURSOR-global-setup.md) for reusing MarkWiki skills/hooks/rules globally in Cursor.

## Corporate safe mode (default on locked-down PCs)

| Disabled (avoids security blocks) | Still works |
|-----------------------------------|-------------|
| Global keyboard hooks (`keyboard` lib) | System tray menu |
| Simulated Ctrl+C / Ctrl+V (`pyautogui`) | Clipboard copy — you press Ctrl+V |
| Opening Explorer from tray | Shows config path in tray title |
| API clients at startup | APIs connect only when you use an action |

**Workflow:** tray → **Start dictate** → speak → **Finish dictate** → text on clipboard → **Ctrl+V** in your app.

**Edit text:** copy selection (Ctrl+C) → tray **Edit clipboard text** → speak instruction → **Finish edit** → Ctrl+V.

To re-enable hotkeys at home, set in `%USERPROFILE%\.whisper\config.yaml`:

```yaml
security:
  corporate_safe_mode: false
  global_hotkeys: true
  synthetic_keystrokes: true
```

## Hotkeys (defaults, only when safe mode is off)

| Action | Default hotkey |
|--------|----------------|
| Dictate | `Ctrl+Shift+Space` (hold) |
| Edit selection | `Ctrl+Shift+E` (hold) |
| Cycle persona | `Ctrl+Shift+P` |
| Remember style | `Ctrl+Shift+R` (hold) |

Change these in `%USERPROFILE%\.whisper\config.yaml`:

```yaml
hotkeys:
  dictate: ctrl+shift+space
  edit_selection: ctrl+shift+e
  cycle_persona: ctrl+shift+p
  remember_style: ctrl+shift+r
```

## Configuration

Config lives in `%USERPROFILE%\.whisper\`:

```
.whisper/
  config.yaml      # hotkeys, providers, behavior
  .env             # API keys (not committed)
  personas/        # work.json, student.json, casual.json
  logs/whisper.log
```

### Provider mix

```yaml
providers:
  stt: openai          # speech-to-text (Whisper API)
  llm: openai          # or anthropic

behavior:
  activation: hold     # hold | toggle (dictate only)
  polish_dictation: true
```

### Personas

Edit `personas/work.json` (or use tray → Personas):

```json
{
  "id": "work",
  "display_name": "Work",
  "system_prompt": "Professional, concise, US English.",
  "style_notes": ["No emojis"],
  "examples": []
}
```

**Learning:**
- After an edit, tray → **Save last edit as example**
- Hold `Ctrl+Shift+R` and say e.g. "remember this: always use bullet points for lists"
- After 10 examples, style notes are auto-consolidated

## Run at logon (optional)

Task Scheduler → Create Task:

- **Trigger:** At log on
- **Action:** Start a program
  - Program: `powershell.exe`
  - Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\whisper\run-whisper.ps1"`
- **Settings:** Run whether user is logged on or not (optional)

## Windows caveats

- Global hotkeys may require **Run as administrator** on some systems (`keyboard` library)
- Paste injection uses clipboard + `Ctrl+V`; may not work in elevated apps or password fields
- Latency is typically 1–4 seconds (network + API)
- Pause from tray during meetings

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No tray icon | Check logs in `%USERPROFILE%\.whisper\logs\whisper.log` |
| Hotkeys not firing | Run terminal as Administrator |
| "OPENAI_API_KEY required" | Set key in `.env` or User environment variables |
| No selection on edit | Highlight text first, then hold edit hotkey |
| No audio | Allow microphone access for Python |

## Project structure

```
whisper/
  whisper/           # Python package
  install.ps1
  run-whisper.ps1
  pyproject.toml
```

## License

MIT (use and modify freely)
