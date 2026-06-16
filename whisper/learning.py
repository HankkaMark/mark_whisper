from __future__ import annotations

import logging
from typing import Callable

from whisper.adapters.base import LLMAdapter, STTAdapter
from whisper.audio import AudioRecorder
from whisper.config import AppConfig
from whisper.personas.schema import PersonaExample
from whisper.personas.store import PersonaStore

logger = logging.getLogger(__name__)

REMEMBER_PREFIXES = ("remember this", "remember that", "save this style", "save style")


class LearningService:
    def __init__(
        self,
        config: AppConfig,
        stt: STTAdapter,
        llm: LLMAdapter,
        recorder: AudioRecorder,
        persona_store: PersonaStore,
        on_status: Callable[[str], None],
    ) -> None:
        self._config = config
        self._stt = stt
        self._llm = llm
        self._recorder = recorder
        self._store = persona_store
        self._on_status = on_status

    def start_remember(self) -> None:
        if self._recorder.is_recording:
            return
        self._on_status("Say what to remember...")
        self._recorder.start()

    def finish_remember(self, persona_id: str) -> None:
        if not self._recorder.is_recording:
            return
        self._on_status("Processing preference...")
        try:
            wav = self._recorder.stop()
            if not wav:
                self._on_status("No audio captured")
                return

            raw = self._stt.transcribe(wav, self._config.behavior.language)
            if not raw:
                self._on_status("No speech detected")
                return

            note = raw
            lower = raw.lower().strip()
            for prefix in REMEMBER_PREFIXES:
                if lower.startswith(prefix):
                    note = raw[len(prefix) :].strip(" :,.")
                    break

            persona = self._store.get(persona_id)
            summarized = self._llm.summarize_style_note(note, persona)
            self._store.add_style_note(persona_id, summarized)
            self._on_status(f"Saved to {persona.display_name}")
            logger.info("Added style note for %s: %s", persona_id, summarized)
        except Exception as exc:
            logger.exception("Remember style failed")
            self._on_status(f"Error: {exc}")

    def save_last_edit_as_example(
        self,
        persona_id: str,
        original: str,
        instruction: str,
        result: str,
    ) -> None:
        example = PersonaExample(
            instruction=instruction,
            before=original[:500],
            after=result[:500],
        )
        self._store.add_example(persona_id, example)
        persona = self._store.get(persona_id)
        self._on_status(f"Example saved to {persona.display_name}")
        if len(persona.examples) >= 10:
            self.maybe_consolidate_style_notes(persona_id)

    def maybe_consolidate_style_notes(self, persona_id: str) -> None:
        persona = self._store.get(persona_id)
        if len(persona.examples) < 10:
            return
        combined = "\n".join(
            f"- {ex.instruction}: {ex.before[:80]} -> {ex.after[:80]}"
            for ex in persona.examples[-5:]
        )
        note = self._llm.summarize_style_note(
            f"Merge these patterns into one style guideline:\n{combined}",
            persona,
        )
        if note and note not in persona.style_notes:
            persona.style_notes.append(note)
            persona.examples = persona.examples[-10:]
            self._store.save(persona)
            logger.info("Consolidated style notes for %s", persona_id)
