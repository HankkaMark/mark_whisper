from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk

from whisper.diagnostics import DiagnosticResult


class DiagnosticsWindow:
    def __init__(self, results: list[DiagnosticResult], log_path: str) -> None:
        self._results = results
        self._log_path = log_path
        self._thread: threading.Thread | None = None

    def show(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        root = tk.Tk()
        root.title("Whisper Diagnostics")
        root.geometry("560x380")
        root.resizable(False, False)

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="System check", font=("", 11, "bold")).pack(anchor=tk.W)

        text = tk.Text(frame, height=14, width=64, wrap=tk.WORD, font=("Consolas", 9))
        text.pack(fill=tk.BOTH, expand=True, pady=8)

        for result in self._results:
            status = "PASS" if result.ok else "FAIL"
            text.insert(tk.END, f"[{status}] {result.category}: {result.summary}\n")
            if result.fix:
                text.insert(tk.END, f"       Fix: {result.fix}\n")
            text.insert(tk.END, "\n")

        text.insert(tk.END, f"Log file: {self._log_path}\n")
        text.config(state=tk.DISABLED)

        ttk.Button(frame, text="Close", command=root.destroy).pack(anchor=tk.E)
        root.mainloop()
