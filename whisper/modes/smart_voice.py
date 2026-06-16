from __future__ import annotations

import logging
from typing import Callable

from whisper.adapters.base import LLMAdapter, STTAdapter
from whisper.audio import AudioRecorder
from whisper.config import AppConfig
from whisper.diagnostics import ErrorReport, format_exception
from whisper.injector import TextInjector
from whisper.personas.schema import Persona

logger = logging.getLogger(__name__)


class SmartVoiceMode:
    """Hold key: edit clipboard text if present, otherwise draft from speech."""

    def __init__(
        self,
        config: AppConfig,
        stt: STTAdapter,
        llm: LLMAdapter,
        recorder: AudioRecorder,
        injector: TextInjector,
        on_status: Callable[[str], None],
        on_error: Callable[[ErrorReport], None] | None = None,
    ) -> None:
        self._config = config
        self._stt = stt
        self._llm = llm
        self._recorder = recorder
        self._injector = injector
        self._on_status = on_status
        self._on_error = on_error
        self._clipboard_at_start: str | None = None
        self.last_edit: tuple[str, str, str, Persona] | None = None

    def _fail(self, report: ErrorReport) -> None:
        self._on_status(f"[{report.category}] {report.summary}")
        if self._on_error:
            self._on_error(report)
        logger.error("[%s] %s — %s", report.category, report.summary, report.detail or report.fix)

    def start_recording(self) -> None:
        if self._recorder.is_recording:
            return
        try:
            self._clipboard_at_start = self._injector.get_selection()
            if self._clipboard_at_start:
                self._on_status("Edit mode — speak your instruction...")
            else:
                self._on_status("Draft mode — speak what you want written...")
            self._recorder.start()
        except Exception as exc:
            report = format_exception(exc)
            if report.category != "Audio":
                report = ErrorReport(
                    "Audio",
                    "Cannot open microphone",
                    "Allow mic access for Python in Windows Settings → Privacy → Microphone.",
                    str(exc),
                )
            self._fail(report)

    def finish_and_apply(self, persona: Persona) -> None:
        if not self._recorder.is_recording:
            self._fail(
                ErrorReport(
                    "App",
                    "Recording already stopped",
                    "Hold the record key while speaking, release when done.",
                )
            )
            return
        self._on_status("Processing...")
        try:
            wav = self._recorder.stop()
            if not wav:
                self._fail(
                    ErrorReport(
                        "Audio",
                        "No audio captured",
                        "Speak while holding the key. Check mic is not muted.",
                    )
                )
                return

            try:
                transcript = self._stt.transcribe(wav, self._config.behavior.language)
            except Exception as exc:
                report = format_exception(exc)
                self._fail(report)
                return

            if not transcript:
                self._fail(
                    ErrorReport(
                        "Audio",
                        "No speech detected",
                        "Speak louder/closer to mic, or check Windows input device.",
                    )
                )
                return

            original = (self._clipboard_at_start or "").strip()
            try:
                if original:
                    result = self._llm.edit_text(original, transcript, persona)
                    self.last_edit = (original, transcript, result, persona)
                    mode = "Edited"
                else:
                    result = self._llm.generate_from_instruction(transcript, persona)
                    mode = "Drafted"
            except Exception as exc:
                self._fail(format_exception(exc))
                return

            msg = self._injector.paste_text(result)
            self._on_status(f"{mode}: {msg} ({persona.display_name})")
            logger.info("%s %d chars from speech", mode, len(result))
        except Exception as exc:
            logger.exception("Smart voice failed")
            self._fail(format_exception(exc))
        finally:
            self._clipboard_at_start = None

    def cancel(self) -> None:
        if self._recorder.is_recording:
            self._recorder.stop()
        self._clipboard_at_start = None
        self._on_status("Cancelled")
