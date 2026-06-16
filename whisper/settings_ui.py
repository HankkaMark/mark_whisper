from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from whisper.config import VOICE_KEYS, AppConfig, save_api_credentials, save_voice_key
from whisper.diagnostics import check_api, check_audio, probe_hotkey_library

logger = logging.getLogger(__name__)


class SettingsWindow:
    def __init__(
        self,
        config: AppConfig,
        on_saved: Callable[[AppConfig], None],
    ) -> None:
        self._config = config
        self._on_saved = on_saved
        self._thread: threading.Thread | None = None

    def show(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        root = tk.Tk()
        root.title("Whisper Settings")
        root.geometry("540x480")
        root.resizable(False, False)

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="API Key", font=("", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 4)
        )
        api_var = tk.StringVar(value=self._config.openai_api_key)
        api_entry = ttk.Entry(frame, textvariable=api_var, width=60, show="*")
        api_entry.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 8))

        show_var = tk.BooleanVar(value=False)

        def toggle_show() -> None:
            api_entry.config(show="" if show_var.get() else "*")

        ttk.Checkbutton(
            frame, text="Show API key", variable=show_var, command=toggle_show
        ).grid(row=2, column=0, sticky=tk.W, pady=(0, 12))

        ttk.Label(frame, text="Gateway URL").grid(row=3, column=0, sticky=tk.W, pady=(0, 4))
        url_var = tk.StringVar(value=self._config.openai_base_url or "")
        ttk.Entry(frame, textvariable=url_var, width=60).grid(
            row=4, column=0, columnspan=2, sticky=tk.EW, pady=(0, 8)
        )

        test_status = tk.StringVar(value="")

        def run_tests() -> None:
            test_status.set("Testing...")
            root.update_idletasks()
            lines: list[str] = []
            cfg = self._config
            cfg.openai_api_key = api_var.get().strip()
            cfg.openai_base_url = url_var.get().strip()
            api_r = check_api(cfg)
            lines.append(f"{'OK' if api_r.ok else 'FAIL'} API: {api_r.summary}")
            audio_r = check_audio()
            lines.append(f"{'OK' if audio_r.ok else 'FAIL'} Audio: {audio_r.summary}")
            hk = key_var.get().strip().lower()
            ok, err = probe_hotkey_library(hk)
            if ok:
                lines.append(f"OK Hotkey: '{hk}' can be registered")
            else:
                lines.append(f"FAIL Hotkey: {err}")
            test_status.set("\n".join(lines))

        ttk.Button(frame, text="Test API / Mic / Hotkey", command=run_tests).grid(
            row=5, column=0, sticky=tk.W, pady=(0, 4)
        )
        ttk.Label(frame, textvariable=test_status, foreground="#444", justify=tk.LEFT).grid(
            row=6, column=0, columnspan=2, sticky=tk.W, pady=(0, 12)
        )

        ttk.Separator(frame).grid(row=7, column=0, columnspan=2, sticky=tk.EW, pady=8)

        ttk.Label(frame, text="Record key (single key, hold to talk)", font=("", 10, "bold")).grid(
            row=8, column=0, sticky=tk.W, pady=(0, 8)
        )

        key_var = tk.StringVar(value=self._config.hotkeys.voice_key)
        key_row = ttk.Frame(frame)
        key_row.grid(row=9, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))
        ttk.Label(key_row, text="Key:").pack(side=tk.LEFT)
        ttk.Combobox(
            key_row,
            textvariable=key_var,
            values=VOICE_KEYS,
            state="readonly",
            width=16,
        ).pack(side=tk.LEFT, padx=8)

        preview_var = tk.StringVar(value=f"Hold {self._config.hotkeys.voice_key} to record")

        def update_preview(*_args) -> None:
            preview_var.set(f"Hold {key_var.get()} to record")

        key_var.trace_add("write", update_preview)
        ttk.Label(frame, textvariable=preview_var, foreground="#555").grid(
            row=10, column=0, sticky=tk.W, pady=(0, 8)
        )

        ttk.Label(
            frame,
            text="Recommended: F8–F12 or Scroll Lock (rarely used by apps).\n"
            "Avoid Ctrl/Alt/Shift — they conflict with normal typing.\n"
            "Edit: Ctrl+C copy text first. Draft: empty clipboard, then hold key.",
            foreground="#666",
            justify=tk.LEFT,
        ).grid(row=11, column=0, columnspan=2, sticky=tk.W, pady=(0, 16))

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=12, column=0, columnspan=2, sticky=tk.E)

        def save() -> None:
            api_key = api_var.get().strip()
            base_url = url_var.get().strip()
            if not api_key:
                messagebox.showerror("Whisper", "API key is required.", parent=root)
                return
            if not base_url:
                messagebox.showerror("Whisper", "Gateway URL is required.", parent=root)
                return
            try:
                save_api_credentials(self._config.data_dir, api_key, base_url)
                hotkeys_saved = save_voice_key(self._config, key_var.get().strip())
                self._config.openai_api_key = api_key
                self._config.openai_base_url = base_url
                self._config.hotkeys = hotkeys_saved
                self._on_saved(self._config)
                messagebox.showinfo(
                    "Whisper",
                    f"Saved. Hold {hotkeys_saved.voice_key} when listening is ON.",
                    parent=root,
                )
                root.destroy()
            except Exception as exc:
                logger.exception("Failed to save settings")
                messagebox.showerror("Whisper", f"Save failed: {exc}", parent=root)

        ttk.Button(btn_row, text="Cancel", command=root.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(btn_row, text="Save", command=save).pack(side=tk.RIGHT)

        frame.columnconfigure(0, weight=1)
        root.mainloop()
