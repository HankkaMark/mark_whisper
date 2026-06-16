from __future__ import annotations

import logging
import time

import pyperclip

logger = logging.getLogger(__name__)


class TextInjector:
    """Paste or copy text. Safe mode uses clipboard only (no simulated keys)."""

    def __init__(
        self,
        clipboard_restore_delay_ms: int = 150,
        synthetic_keystrokes: bool = False,
    ) -> None:
        self._delay = clipboard_restore_delay_ms / 1000.0
        self._synthetic = synthetic_keystrokes

    def get_selection(self) -> str | None:
        if self._synthetic:
            return self._get_selection_via_keys()
        return self._get_clipboard_text()

    def _get_clipboard_text(self) -> str | None:
        try:
            text = pyperclip.paste()
            if text and str(text).strip():
                return str(text).strip()
        except pyperclip.PyperclipException as exc:
            logger.warning("Clipboard read failed: %s", exc)
        return None

    def _get_selection_via_keys(self) -> str | None:
        import pyautogui

        pyautogui.PAUSE = 0.02
        pyautogui.FAILSAFE = False
        backup = pyperclip.paste()
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.15)
        selected = pyperclip.paste()
        if backup:
            pyperclip.copy(backup)
        if selected and str(selected).strip():
            return str(selected).strip()
        return None

    def paste_text(self, text: str) -> str:
        """Apply text. Returns a short status message for the tray."""
        if self._synthetic:
            return self._paste_via_keys(text)
        return self._paste_clipboard_only(text)

    def _paste_clipboard_only(self, text: str) -> str:
        pyperclip.copy(text)
        return "Copied to clipboard — press Ctrl+V to paste"

    def _paste_via_keys(self, text: str) -> str:
        import pyautogui

        pyautogui.PAUSE = 0.02
        pyautogui.FAILSAFE = False
        backup = pyperclip.paste()
        try:
            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(self._delay)
            return "Pasted"
        finally:
            if backup:
                pyperclip.copy(backup)
