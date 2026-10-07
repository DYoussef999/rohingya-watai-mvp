"""Runs the configured stages on one recording."""

from __future__ import annotations

from dataclasses import dataclass, replace

from rohingya_translate.audio import Audio
from rohingya_translate.config import Config
from rohingya_translate.registry import create_backend
from rohingya_translate.stages.base import (
    SpeechToText,
    SpeechTranslator,
    Synthesizer,
    TextResult,
    TextTranslator,
)


@dataclass
class Translation:
    """Everything the pipeline produced for one recording."""

    english: TextResult
    transcript: TextResult | None = None  # Rohingya text, cascade mode only
    speech: Audio | None = None  # spoken English, if a synthesizer is set


class Pipeline:
    """Speech -> English, either directly or via a Rohingya transcript."""

    def __init__(self, config: Config) -> None:
        self.config = config
        if config.mode == "direct":
            self.speech_translator = create_backend(config.speech_translator, SpeechTranslator)
        else:
            self.speech_to_text = create_backend(config.speech_to_text, SpeechToText)
            self.text_translator = create_backend(config.text_translator, TextTranslator)
        self.synthesizer = (
            create_backend(replace(config.voice, backend=config.synthesizer), Synthesizer)
            if config.synthesizer
            else None
        )

    def run(self, audio: Audio, speak: bool = True) -> Translation:
        """Translate one recording. ``speak=False`` skips reading it aloud (do it later)."""
        if self.config.mode == "direct":
            result = Translation(english=self.speech_translator.translate_speech(audio))
        else:
            transcript = self.speech_to_text.transcribe(audio)
            english = self.text_translator.translate_text(transcript)
            result = Translation(english=english, transcript=transcript)

        if speak and self.synthesizer:
            result.speech = self.synthesizer.synthesize(result.english.text)
        return result
