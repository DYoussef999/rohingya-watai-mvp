"""Stub backends with no models, for tests and for wiring up the pipeline."""

from __future__ import annotations

import numpy as np

from rohingya_translate.audio import Audio
from rohingya_translate.config import StageConfig
from rohingya_translate.stages.base import Label, Segment, TextResult


class EchoBackend:
    """Describes the audio instead of understanding it. Implements every stage."""

    def __init__(self, config: StageConfig | None = None) -> None:
        self.config = config or StageConfig()
        self.name = "echo"

    def translate_speech(self, audio: Audio) -> TextResult:
        return self._describe(audio, language="en")

    def transcribe(self, audio: Audio) -> TextResult:
        return self._describe(audio, language="rhg")

    def translate_text(self, text: TextResult) -> TextResult:
        return TextResult(text=f"[en] {text.text}", language="en", segments=text.segments)

    def synthesize(self, text: str) -> Audio:
        return Audio(np.zeros(0, dtype=np.float32))

    def embed(self, audio: Audio) -> np.ndarray:
        """Coarse spectrum shape: identical clips match, different tones don't. Not for real use."""
        spectrum = np.abs(np.fft.rfft(audio.samples, n=4096))
        bands = np.array([band.sum() for band in np.array_split(spectrum, 64)], dtype=np.float32)
        norm = np.linalg.norm(bands)
        return bands / norm if norm else bands

    def label_image(self, image: np.ndarray, candidates: list[str]) -> list[Label]:
        """Sees nothing: every candidate scores 0."""
        return [Label(c, 0.0) for c in candidates]

    def _describe(self, audio: Audio, language: str) -> TextResult:
        text = f"<{audio.duration:.1f}s of audio>"
        return TextResult(text, language, [Segment(0.0, audio.duration, text)], confidence=0.0)
