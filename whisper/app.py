from __future__ import annotations

import logging
import threading
from pathlib import Path

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from whisper.adapters.base import build_llm, build_stt
from whisper.audio import AudioRecorder
from whisper.config import AppConfig, load_config, save_active_persona
from whisper.diagnostics import (
    ErrorReport,
    StatusBoard,
    format_exception,
    probe_hotkey_library,
    run_all_checks,
    summarize,
)
from whisper.diagnostics_ui import DiagnosticsWindow
from whisper.hotkeys import create_hotkey_manager
from whisper.injector import TextInjector
from whisper.learning import LearningService
from whisper.modes.dictate import DictateMode
from whisper.modes.edit_selection import EditSelectionMode
from whisper.modes.smart_voice import SmartVoiceMode
from whisper.personas.store import PersonaStore
from whisper.settings_ui import SettingsWindow

logger = logging.getLogger(__name__)


def _setup_logging(logs_dir: Path, console: bool = False) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "whisper.log"
    handlers: list[logging.Handler] = [
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    if console:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def _make_icon_image(color: str = "#4A90D9", listening: bool = True) -> Image.Image:
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    fill = color if listening else "#888888"
    draw.ellipse((8, 8, size - 8, size - 8), fill=fill)
    return image


class WhisperApp:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()
        sec = self.config.security
        _setup_logging(self.config.logs_dir, console=not sec.corporate_safe_mode)

        self.board = StatusBoard()
        self.persona_store = PersonaStore(self.config.personas_dir)
        self._stt = None
        self._llm = None
        self.recorder = AudioRecorder()
        self.injector = TextInjector(
            self.config.behavior.clipboard_restore_delay_ms,
            synthetic_keystrokes=sec.use_synthetic_keys,
        )
        self.hotkeys = create_hotkey_manager(sec.use_hotkeys)

        self._listening_active = True
        self._voice_recording = False
        self._lock = threading.Lock()
        self._dictate_active = False
        self._edit_active = False
        self._remember_active = False
        self._hotkey_probe_error: str | None = None

        self._modes_ready = False
        self._icon: Icon | None = None
        self._settings = SettingsWindow(self.config, self._on_settings_saved)

    def _ensure_modes(self) -> None:
        if self._modes_ready:
            return
        self.smart_voice = SmartVoiceMode(
            self.config,
            self.stt,
            self.llm,
            self.recorder,
            self.injector,
            self.set_status,
            on_error=self.report_error,
        )
        self.dictate = DictateMode(
            self.config,
            self.stt,
            self.llm,
            self.recorder,
            self.injector,
            self.set_status,
        )
        self.edit_mode = EditSelectionMode(
            self.config,
            self.stt,
            self.llm,
            self.recorder,
            self.injector,
            self.set_status,
        )
        self.learning = LearningService(
            self.config,
            self.stt,
            self.llm,
            self.recorder,
            self.persona_store,
            self.set_status,
        )
        self._modes_ready = True

    def _reset_api_clients(self) -> None:
        self._stt = None
        self._llm = None
        self._modes_ready = False

    def _on_settings_saved(self, config: AppConfig) -> None:
        self.config = config
        self._reset_api_clients()
        self.hotkeys.unregister_all()
        self.hotkeys = create_hotkey_manager(self.config.security.use_hotkeys)
        if self._listening_active:
            self._register_hotkeys()
        self._run_diagnostics(notify=False)
        self._update_tray_appearance()
        self._update_menu()
        hk = self.config.hotkeys.voice_key
        self.set_status(f"Settings saved — hold {hk} when listening")

    @property
    def stt(self):
        if self._stt is None:
            self._stt = build_stt(self.config)
        return self._stt

    @property
    def llm(self):
        if self._llm is None:
            self._llm = build_llm(self.config)
        return self._llm

    @property
    def active_persona_id(self) -> str:
        return self.config.active_persona

    def active_persona(self):
        return self.persona_store.get(self.active_persona_id)

    def set_status(self, message: str) -> None:
        self.board.set_status(message)
        logger.info("Status: %s", message)
        if self._icon:
            self._icon.title = self._tray_title()
        self._update_menu()

    def report_error(self, report: ErrorReport, *, notify: bool = True) -> None:
        self.board.set_error(report)
        logger.error("[%s] %s | fix: %s", report.category, report.summary, report.fix)
        if self._icon:
            self._icon.title = self._tray_title()
            if notify:
                self._notify(f"[{report.category}] {report.summary}", report.fix)
        self._update_menu()

    def _notify(self, title: str, message: str) -> None:
        if not self._icon:
            return
        try:
            self._icon.notify(message or title, title)
        except Exception:
            logger.debug("Tray notification not available")

    def _tray_title(self) -> str:
        persona = self.active_persona()
        state = "ON" if self._listening_active else "OFF"
        hk = self.config.hotkeys.voice_key
        if self.board.last_error:
            return f"Whisper [{state}] — [{self.board.last_error.category}] {self.board.last_error.summary}"
        return f"Whisper [{state}] — hold {hk} — {persona.display_name}"

    def _run_async(self, fn) -> None:
        threading.Thread(target=fn, daemon=True).start()

    def _get_persona(self):
        return self.persona_store.get(self.active_persona_id)

    def start_listening(self) -> None:
        if self._listening_active:
            self.set_status(f"Already listening — hold {self.config.hotkeys.voice_key}")
            return
        self._listening_active = True
        self._register_hotkeys()
        self._run_diagnostics(notify=False)
        self._update_tray_appearance()
        self.set_status(f"Listening ON — hold {self.config.hotkeys.voice_key}")

    def stop_listening(self) -> None:
        if not self._listening_active:
            self.set_status("Already stopped — hotkey disabled")
            return
        if self._voice_recording:
            self._voice_release()
        self._listening_active = False
        self.hotkeys.unregister_all()
        self._run_diagnostics(notify=False)
        self._update_tray_appearance()
        self.set_status("Listening OFF — tray → Start listening to re-enable")

    def open_settings(self) -> None:
        self._settings = SettingsWindow(self.config, self._on_settings_saved)
        self._settings.show()

    def open_diagnostics(self) -> None:
        self._run_diagnostics(notify=False)
        log_path = str(self.config.logs_dir / "whisper.log")
        DiagnosticsWindow(self.board.diagnostics, log_path).show()

    def _run_diagnostics(self, *, notify: bool = True) -> None:
        def _work() -> None:
            results = run_all_checks(
                self.config,
                listening=self._listening_active,
                hotkey_registered=self.hotkeys.is_registered,
                hotkey_error=self._hotkey_probe_error or self.hotkeys.last_register_error,
                hooks_enabled=self.config.security.use_hotkeys,
            )
            self.board.diagnostics = results
            failed = [r for r in results if not r.ok]
            if failed and notify:
                first = failed[0]
                self.report_error(
                    ErrorReport(first.category, first.summary, first.fix),
                    notify=True,
                )
            elif not failed:
                self.board.clear_error()
                summary = summarize(results)
                self.set_status(f"Diagnostics OK — hold {self.config.hotkeys.voice_key}")
                logger.info("Diagnostics: %s", summary)
            self._update_menu()

        self._run_async(_work)

    def _voice_press(self) -> None:
        if not self._listening_active:
            self.report_error(
                ErrorReport("Hotkey", "Key pressed but listening is OFF", "Tray → Start listening."),
                notify=True,
            )
            return
        self._ensure_modes()
        with self._lock:
            if self._voice_recording or self._dictate_active or self._edit_active:
                return
            self._voice_recording = True
        self.board.clear_error()
        self.set_status(f"Recording — release {self.config.hotkeys.voice_key} when done")
        try:
            self.smart_voice.start_recording()
        except Exception as exc:
            self._voice_recording = False
            self.report_error(format_exception(exc))

    def _voice_release(self) -> None:
        with self._lock:
            if not self._voice_recording:
                return
            self._voice_recording = False
        self._run_async(lambda: self.smart_voice.finish_and_apply(self._get_persona()))

    def tray_start_dictate(self) -> None:
        self._ensure_modes()
        with self._lock:
            if self._dictate_active:
                return
            self._dictate_active = True
        self.dictate.start_recording()

    def tray_finish_dictate(self) -> None:
        self._ensure_modes()
        with self._lock:
            if not self._dictate_active:
                self.set_status("Not recording — use Start dictate first")
                return
            self._dictate_active = False
        self._run_async(lambda: self.dictate.finish_and_inject(self._get_persona()))

    def tray_start_edit(self) -> None:
        self._ensure_modes()
        with self._lock:
            if self._edit_active or self._dictate_active:
                return
            self._edit_active = True
        self._run_async(lambda: self.edit_mode.start_edit(self._get_persona()))

    def tray_finish_edit(self) -> None:
        self._ensure_modes()
        with self._lock:
            if not self._edit_active:
                self.set_status("Not recording — use Edit clipboard first")
                return
            self._edit_active = False
        self._run_async(lambda: self.edit_mode.finish_edit(self._get_persona()))

    def tray_start_remember(self) -> None:
        self._ensure_modes()
        with self._lock:
            if self._remember_active:
                return
            self._remember_active = True
        self.learning.start_remember()

    def tray_finish_remember(self) -> None:
        self._ensure_modes()
        with self._lock:
            if not self._remember_active:
                self.set_status("Not recording — use Remember style first")
                return
            self._remember_active = False
            pid = self.active_persona_id
        self._run_async(lambda: self.learning.finish_remember(pid))

    def cycle_persona(self) -> None:
        next_id = self.persona_store.cycle_next(self.active_persona_id)
        self.set_persona(next_id)

    def set_persona(self, persona_id: str) -> None:
        save_active_persona(self.config, persona_id)
        persona = self.persona_store.get(persona_id)
        self.set_status(f"Persona: {persona.display_name}")

    def save_last_edit_example(self) -> None:
        self._ensure_modes()
        last = None
        if self._modes_ready:
            last = self.smart_voice.last_edit or self.edit_mode.last_edit
        if not last:
            self.set_status("No recent edit to save")
            return
        original, instruction, result, persona = last
        self.learning.save_last_edit_as_example(
            persona.id, original, instruction, result
        )

    def show_config_path(self) -> None:
        path = str(self.config.data_dir)
        if self.config.security.open_config_in_explorer:
            import os

            os.startfile(path)
        else:
            self.set_status(f"Config folder: {path}")

    def _register_hotkeys(self) -> None:
        self.hotkeys.unregister_all()
        self._hotkey_probe_error = None

        if not self._listening_active or not self.config.security.use_hotkeys:
            self._run_diagnostics(notify=False)
            return

        hk = self.config.hotkeys.voice_key
        ok, probe_err = probe_hotkey_library(hk)
        if not ok:
            self._hotkey_probe_error = probe_err
            self.report_error(
                ErrorReport("Hotkey", f"Cannot use '{hk}'", probe_err),
                notify=True,
            )
            self._run_diagnostics(notify=False)
            return

        if self.hotkeys.register_hold(hk, self._voice_press, self._voice_release):
            self.board.clear_error()
            logger.info("Voice hotkey active: %s", hk)
        else:
            err = self.hotkeys.last_register_error or "Unknown registration error"
            self._hotkey_probe_error = err
            self.report_error(
                ErrorReport(
                    "Hotkey",
                    f"'{hk}' failed to register",
                    "Use tray Manual actions, or run as Administrator.",
                ),
                notify=True,
            )

        self._run_diagnostics(notify=False)

    def _persona_menu_items(self) -> list:
        items = []
        for pid in self.persona_store.list_ids():
            persona = self.persona_store.get(pid)

            def make_handler(persona_id: str):
                return lambda: self.set_persona(persona_id)

            def make_checked(persona_id: str):
                return lambda _item: persona_id == self.active_persona_id

            items.append(
                MenuItem(
                    persona.display_name,
                    make_handler(pid),
                    checked=make_checked(pid),
                    radio=True,
                )
            )
        return items

    def _manual_actions_menu(self) -> Menu:
        return Menu(
            MenuItem("Start dictate (mic)", self.tray_start_dictate),
            MenuItem("Finish dictate → clipboard", self.tray_finish_dictate),
            Menu.SEPARATOR,
            MenuItem("Edit clipboard text (mic)", self.tray_start_edit),
            MenuItem("Finish edit → clipboard", self.tray_finish_edit),
            Menu.SEPARATOR,
            MenuItem("Remember style — start", self.tray_start_remember),
            MenuItem("Remember style — finish", self.tray_finish_remember),
        )

    def _diagnostics_menu_items(self) -> list:
        items = []
        for result in self.board.diagnostics:
            items.append(
                MenuItem(
                    lambda _item, line=result.tray_line(): line,
                    None,
                    enabled=False,
                )
            )
        if not items:
            items.append(MenuItem("No diagnostics yet", None, enabled=False))
        return items

    def _update_tray_appearance(self) -> None:
        if not self._icon:
            return
        self._icon.icon = _make_icon_image(listening=self._listening_active)
        self._icon.title = self._tray_title()

    def _update_menu(self) -> None:
        if self._icon:
            self._icon.menu = self._build_menu()

    def _build_menu(self) -> Menu:
        persona = self.active_persona()
        hk = self.config.hotkeys.voice_key
        items = [
            MenuItem(lambda _item: f"Persona: {persona.display_name}", None, enabled=False),
            MenuItem(lambda _item: f"Status: {self.board.status}", None, enabled=False),
            MenuItem(lambda _item: f"Key: hold {hk}", None, enabled=False),
        ]
        if self.board.error_line():
            items.append(MenuItem(lambda _item: self.board.error_line(), None, enabled=False))
        if self.board.fix_line():
            items.append(MenuItem(lambda _item: self.board.fix_line(), None, enabled=False))
        items.extend(
            [
                Menu.SEPARATOR,
                MenuItem(
                    "Start listening",
                    self.start_listening,
                    checked=lambda _item: self._listening_active,
                    radio=True,
                ),
                MenuItem(
                    "Stop listening",
                    self.stop_listening,
                    checked=lambda _item: not self._listening_active,
                    radio=True,
                ),
                MenuItem("Settings...", self.open_settings),
                MenuItem("Run diagnostics", self.open_diagnostics),
                MenuItem("Diagnostics", Menu(*self._diagnostics_menu_items())),
                Menu.SEPARATOR,
                MenuItem("Manual actions (no hotkey)", self._manual_actions_menu()),
                Menu.SEPARATOR,
                MenuItem("Personas", Menu(*self._persona_menu_items())),
                MenuItem("Save last edit as example", self.save_last_edit_example),
                MenuItem("Show config folder path", self.show_config_path),
                Menu.SEPARATOR,
                MenuItem("Quit", self.quit),
            ]
        )
        return Menu(*items)

    def _build_tray_icon(self) -> Icon:
        return Icon(
            "whisper",
            _make_icon_image(listening=self._listening_active),
            self._tray_title(),
            menu=self._build_menu(),
        )

    def quit(self) -> None:
        if self._voice_recording and self._modes_ready:
            self.smart_voice.cancel()
        self.hotkeys.unregister_all()
        if self._icon:
            self._icon.stop()

    def run(self) -> None:
        self._register_hotkeys()
        hk = self.config.hotkeys.voice_key
        if self._listening_active:
            self.set_status(f"Listening ON — hold {hk}")
        else:
            self.set_status("Listening OFF")
        logger.info("Whisper running (listening=%s, key=%s)", self._listening_active, hk)
        self._icon = self._build_tray_icon()
        self._run_diagnostics(notify=True)
        self._icon.run()
