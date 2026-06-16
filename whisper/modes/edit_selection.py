from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from whisper.adapters.base import LLMAdapter, STTAdapter
from whisper.audio import AudioRecorder
from whisper.config import AppConfig
from whisper.injector import TextInjector
from whisper.personas.schema import Persona

logger = logging.getLogger(__name__)


@dataclass
class PendingEdit:
    original: str
    persona_id: str


class EditSelectionMode:
    def __init__(
        self,
        config: AppConfig,
        stt: STTAdapter,
        llm: LLMAdapter,
        recorder: AudioRecorder,
        injector: TextInjector,
        on_status: Callable[[str], None],
    ) -> None:
        self._config = config
        self._stt = stt
        self._llm = llm
        self._recorder = recorder
        self._injector = injector
        self._on_status = on_status
        self._pending: PendingEdit | None = None
        self.last_edit: tuple[str, str, str, Persona] | None = None

    def start_edit(self, persona: Persona) -> None:
        if self._recorder.is_recording:
            return
        selected = self._injector.get_selection()
        if not selected or not selected.strip():
            self._on_status("Clipboard empty — copy text first (Ctrl+C), then try again")
            return
        self._on_status("Using clipboard text — speak your edit instruction...")
        self._pending = PendingEdit(original=selected, persona_id=persona.id)
        self._on_status("Listening for edit instruction...")
        self._recorder.start()

    def finish_edit(self, persona: Persona) -> None:
        if not self._pending:
            return
        if not self._recorder.is_recording:
            return

        self._on_status("Processing edit...")
        try:
            wav = self._recorder.stop()
            if not wav:
                self._on_status("No audio captured")
                self._pending = None
                return

            instruction = self._stt.transcribe(wav, self._config.behavior.language)
            if not instruction:
                self._on_status("No instruction detected")
                self._pending = None
                return

            original = self._pending.original
            result = self._llm.edit_text(original, instruction, persona)
            msg = self._injector.paste_text(result)

            self.last_edit = (original, instruction, result, persona)
            self._on_status(f"{msg} ({persona.display_name})")
            logger.info("Edited text with instruction: %s", instruction[:80])
        except Exception as exc:
            logger.exception("Edit failed")
            self._on_status(f"Error: {exc}")
        finally:
            self._pending = None

    def cancel(self) -> None:
        if self._recorder.is_recording:
            self._recorder.stop()
        self._pending = None
        self._on_status("Edit cancelled")
