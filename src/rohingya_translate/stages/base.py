"""Interfaces every stage backend implements.

The pipeline only talks to these protocols, so a new model (a fine-tuned
Whisper, a different ASR, a TTS voice, a vision model) is a new class plus one
line in ``registry.py``. Nothing else changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np

from rohingya_translate.audio import Audio


@dataclass
class Segment:
    """A stretch of speech and its text, with times in seconds."""

    start: float
    end: float
    text: str


@dataclass
class TextResult:
    """Text produced by a stage, with optional timing and confidence."""

    text: str
    language: str
    segments: list[Segment] = field(default_factory=list)
    confidence: float | None = None


@dataclass
class Label:
    """A candidate English label for an image, scored 0-1 (independently, not summing to 1)."""

    text: str
    score: float


@runtime_checkable
class SpeechTranslator(Protocol):
    """Speech in one language -> English text, in a single model ("direct" mode)."""

    def translate_speech(self, audio: Audio) -> TextResult: ...


@runtime_checkable
class SpeechToText(Protocol):
    """Speech -> transcript in the spoken language ("cascade" mode, step 1)."""

    def transcribe(self, audio: Audio) -> TextResult: ...


@runtime_checkable
class TextTranslator(Protocol):
    """Rohingya text -> English text ("cascade" mode, step 2)."""

    def translate_text(self, text: TextResult) -> TextResult: ...


@runtime_checkable
class Synthesizer(Protocol):
    """English text -> speech, to read the translation aloud."""

    def synthesize(self, text: str) -> Audio: ...


@runtime_checkable
class ImageTextReader(Protocol):
    """Image -> text found in it (e.g. Hanifi Rohingya signage). Not wired in yet."""

    def read_image(self, image: np.ndarray) -> TextResult: ...


@runtime_checkable
class ImageLabeler(Protocol):
    """Image (H x W x 3 RGB uint8) -> how well each candidate English label fits, best first."""

    def label_image(self, image: np.ndarray, candidates: list[str]) -> list[Label]: ...


@runtime_checkable
class AudioEmbedder(Protocol):
    """Speech clip -> unit-length vector. Clips of the same word should land close together."""

    def embed(self, audio: Audio) -> np.ndarray: ...
