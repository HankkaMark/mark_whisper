# AGENTS.md — Whisper voice assistant

## Goal

Windows tray app for voice dictate and edit. Corporate PCs use **safe mode** (tray + clipboard only).

## Commands

| Action | How (safe mode) |
|--------|-----------------|
| Start app | Double-click `START-whisper.vbs` (preferred — no cmd.exe) |
| Install deps | One-time: IT runs `tools\bootstrap_install.py` with approved Python |
| Config | `%USERPROFILE%\.whisper\config.yaml` and `.env` |

## Engineering rules

- Do **not** enable `keyboard` / `pyautogui` on locked-down machines unless security approves.
- API keys only in `%USERPROFILE%\.whisper\.env` — never commit.
- Use company AI gateway via `OPENAI_BASE_URL` + `OPENAI_API_KEY` in `.env`.
- Prefer minimal diffs; match existing Python style in `whisper/`.

## Validation

- `python -c "from whisper.config import load_config; load_config()"` after config changes.
- Manual: tray → Start dictate → Finish → Ctrl+V in Notepad.

## Safety

- No install/download at runtime.
- No global hotkeys or synthetic keystrokes when `security.corporate_safe_mode: true`.

## Language

- Reply to the owner in **Chinese** unless they write in English.
- Code comments and README can be bilingual; user-facing tray status in English is OK.
