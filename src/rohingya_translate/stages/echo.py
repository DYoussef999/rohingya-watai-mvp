"""Stub backends with no models, for tests and for wiring up the pipeline."""

from __future__ import annotations

import numpy as np

from rohingya_translate.audio import Audio
from rohingya_translate.config import StageConfig
from rohingya_translate.stages.base import Segment, TextResult


class EchoBackend:
    """Describes the audio instead of understanding it. Implements every stage."""

    def __init__(self, config: StageConfig | None = None) -> None:
        self.config = config or StageConfig()

    def translate_speech(self, audio: Audio) -> TextResult:
        return self._describe(audio, language="en")

    def transcribe(self, audio: Audio) -> TextResult:
        return self._describe(audio, language="rhg")

    def translate_text(self, text: TextResult) -> TextResult:
        return TextResult(text=f"[en] {text.text}", language="en", segments=text.segments)

    def synthesize(self, text: str) -> Audio:
        return Audio(np.zeros(0, dtype=np.float32))

    def _describe(self, audio: Audio, language: str) -> TextResult:
        text = f"<{audio.duration:.1f}s of audio>"
        return TextResult(text, language, [Segment(0.0, audio.duration, text)], confidence=0.0)
