from __future__ import annotations

import io

from openai import OpenAI


class OpenAISTTAdapter:
    def __init__(
        self,
        api_key: str,
        model: str = "whisper-1",
        base_url: str | None = None,
    ) -> None:
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model

    def transcribe(self, wav_bytes: bytes, language: str | None = None) -> str:
        audio_file = io.BytesIO(wav_bytes)
        audio_file.name = "audio.wav"
        kwargs: dict = {"model": self._model, "file": audio_file}
        if language:
            kwargs["language"] = language
        response = self._client.audio.transcriptions.create(**kwargs)
        return (response.text or "").strip()
