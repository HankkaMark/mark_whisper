from __future__ import annotations

import logging
from typing import Callable, Protocol

logger = logging.getLogger(__name__)


class HotkeyManagerProtocol(Protocol):
    @property
    def paused(self) -> bool: ...

    @property
    def last_register_error(self) -> str | None: ...

    @property
    def is_registered(self) -> bool: ...

    def set_paused(self, paused: bool) -> None: ...

    def register_hold(
        self,
        hotkey: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> bool: ...

    def register_press(self, hotkey: str, callback: Callable[[], None]) -> bool: ...

    def unregister_all(self) -> None: ...


class NoOpHotkeyManager:
    """Tray-only mode: no global keyboard hooks."""

    def __init__(self) -> None:
        self._paused = False
        self._last_error = "Hotkeys disabled"
        self._registered = False

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def last_register_error(self) -> str | None:
        return self._last_error

    @property
    def is_registered(self) -> bool:
        return False

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def register_hold(
        self,
        hotkey: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> bool:
        self._last_error = "Hotkeys disabled in config"
        logger.debug("Hotkeys disabled; ignoring hold binding %s", hotkey)
        return False

    def register_press(self, hotkey: str, callback: Callable[[], None]) -> bool:
        self._last_error = "Hotkeys disabled in config"
        return False

    def unregister_all(self) -> None:
        pass


class HotkeyManager:
    """Global hotkeys via keyboard library."""

    def __init__(self) -> None:
        self._hooks: list = []
        self._paused = False
        self._keyboard = None
        self._last_error: str | None = None
        self._registered = False

    def _kb(self):
        if self._keyboard is None:
            import keyboard

            self._keyboard = keyboard
        return self._keyboard

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def last_register_error(self) -> str | None:
        return self._last_error

    @property
    def is_registered(self) -> bool:
        return self._registered

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def register_hold(
        self,
        hotkey: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> bool:
        self.unregister_all()
        kb = self._kb()
        key = hotkey.strip().lower()

        def press_wrapper(_event=None) -> None:
            if not self._paused:
                on_press()

        def release_wrapper(_event=None) -> None:
            if not self._paused:
                on_release()

        try:
            if "+" in key:
                kb.add_hotkey(key, press_wrapper, suppress=False, trigger_on_release=False)
                kb.add_hotkey(key, release_wrapper, suppress=False, trigger_on_release=True)
            else:
                hook_press = kb.on_press_key(key, press_wrapper, suppress=False)
                hook_release = kb.on_release_key(key, release_wrapper, suppress=False)
                self._hooks.extend([hook_press, hook_release])
            self._registered = True
            self._last_error = None
            logger.info("Registered hold hotkey: %s", key)
            return True
        except Exception as exc:
            self._registered = False
            self._last_error = str(exc)
            logger.exception("Failed to register hotkey %s", key)
            return False

    def register_press(self, hotkey: str, callback: Callable[[], None]) -> bool:
        kb = self._kb()

        def wrapper() -> None:
            if not self._paused:
                callback()

        try:
            kb.add_hotkey(hotkey, wrapper, suppress=False)
            self._registered = True
            self._last_error = None
            logger.info("Registered press hotkey: %s", hotkey)
            return True
        except Exception as exc:
            self._last_error = str(exc)
            logger.exception("Failed to register press hotkey %s", hotkey)
            return False

    def unregister_all(self) -> None:
        if not self._keyboard:
            self._registered = False
            return
        try:
            self._keyboard.unhook_all()
        except Exception:
            pass
        self._hooks.clear()
        self._registered = False


def create_hotkey_manager(enabled: bool) -> HotkeyManagerProtocol:
    if enabled:
        return HotkeyManager()
    return NoOpHotkeyManager()
