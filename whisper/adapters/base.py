from __future__ import annotations

from typing import Protocol

from whisper.config import AppConfig
from whisper.personas.schema import Persona


class STTAdapter(Protocol):
    def transcribe(self, wav_bytes: bytes, language: str | None = None) -> str: ...


class LLMAdapter(Protocol):
    def polish_dictation(self, text: str, persona: Persona) -> str: ...

    def edit_text(self, original: str, instruction: str, persona: Persona) -> str: ...

    def generate_from_instruction(self, instruction: str, persona: Persona) -> str: ...

    def summarize_style_note(self, note: str, persona: Persona) -> str: ...


def build_stt(config: AppConfig) -> STTAdapter:
    from whisper.adapters.openai_stt import OpenAISTTAdapter

    provider = config.providers_stt.lower()
    if provider == "openai":
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for speech-to-text")
        return OpenAISTTAdapter(
            config.openai_api_key,
            config.openai_stt_model,
            config.openai_base_url,
        )
    raise ValueError(f"Unsupported STT provider: {provider}")


def build_llm(config: AppConfig) -> LLMAdapter:
    from whisper.adapters.anthropic_llm import AnthropicLLMAdapter
    from whisper.adapters.openai_llm import OpenAILLMAdapter

    provider = config.providers_llm.lower()
    if provider == "openai":
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for LLM")
        return OpenAILLMAdapter(
            config.openai_api_key,
            config.openai_llm_model,
            config.openai_base_url,
        )
    if provider == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for LLM")
        return AnthropicLLMAdapter(config.anthropic_api_key, config.anthropic_model)
    raise ValueError(f"Unsupported LLM provider: {provider}")
