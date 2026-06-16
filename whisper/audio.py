from __future__ import annotations

import io
import logging
import wave
from threading import Lock

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1


class AudioRecorder:
    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self.sample_rate = sample_rate
        self._lock = Lock()
        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._recording = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    def _callback(self, indata: np.ndarray, _frames: int, _time, status) -> None:
        if status:
            logger.warning("Audio status: %s", status)
        with self._lock:
            if self._recording:
                self._frames.append(indata.copy())

    def start(self) -> None:
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()
        except Exception:
            with self._lock:
                self._recording = False
            raise
        logger.debug("Recording started")

    def stop(self) -> bytes | None:
        with self._lock:
            self._recording = False
            frames = list(self._frames)
            self._frames = []

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not frames:
            logger.debug("No audio captured")
            return None

        audio = np.concatenate(frames, axis=0)
        if audio.size == 0:
            return None

        pcm = (audio.flatten() * 32767).astype(np.int16)
        return _pcm_to_wav(pcm.tobytes(), self.sample_rate)


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buffer.getvalue()
