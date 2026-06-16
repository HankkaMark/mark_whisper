from __future__ import annotations

import logging
from typing import Callable

from whisper.adapters.base import LLMAdapter, STTAdapter
from whisper.audio import AudioRecorder
from whisper.config import AppConfig
from whisper.injector import TextInjector
from whisper.personas.schema import Persona

logger = logging.getLogger(__name__)


class DictateMode:
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

    def start_recording(self) -> None:
        if self._recorder.is_recording:
            return
        self._on_status("Listening...")
        self._recorder.start()

    def finish_and_inject(self, persona: Persona) -> None:
        if not self._recorder.is_recording:
            return
        self._on_status("Processing...")
        try:
            wav = self._recorder.stop()
            if not wav:
                self._on_status("No audio captured")
                return

            transcript = self._stt.transcribe(wav, self._config.behavior.language)
            if not transcript:
                self._on_status("No speech detected")
                return

            text = transcript
            if self._config.behavior.polish_dictation:
                text = self._llm.polish_dictation(transcript, persona)

            msg = self._injector.paste_text(text)
            self._on_status(f"{msg} ({persona.display_name})")
            logger.info("Dictated %d chars", len(text))
        except Exception as exc:
            logger.exception("Dictate failed")
            self._on_status(f"Error: {exc}")
