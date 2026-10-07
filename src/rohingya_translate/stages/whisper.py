"""Whisper backend via faster-whisper (MIT). Install with ``pip install -e ".[whisper]"``.

Off-the-shelf Whisper has never seen Rohingya, so expect poor output until a
fine-tuned model is pointed to with ``model = "models/<name>"`` in the config.
It is still useful now as a baseline and for testing the plumbing.
"""

from __future__ import annotations

from rohingya_translate.audio import Audio
from rohingya_translate.config import StageConfig
from rohingya_translate.stages.base import Segment, TextResult


class WhisperBackend:
    """Implements SpeechTranslator (task="translate") and SpeechToText (task="transcribe")."""

    def __init__(self, config: StageConfig) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise ImportError('Whisper backend needs: pip install -e ".[whisper]"') from e

        self.config = config
        compute_type = config.options.get("compute_type", "default")
        self.model = WhisperModel(
            config.model or "small", device=config.device, compute_type=compute_type
        )

    def translate_speech(self, audio: Audio) -> TextResult:
        result = self._run(audio, task="translate")
        result.language = "en"
        return result

    def transcribe(self, audio: Audio) -> TextResult:
        return self._run(audio, task="transcribe")

    def _run(self, audio: Audio, task: str) -> TextResult:
        segments, info = self.model.transcribe(
            audio.samples,
            task=task,
            language=self.config.source_language or None,
            beam_size=self.config.options.get("beam_size", 5),
            vad_filter=self.config.options.get("vad_filter", True),
        )
        segs = [Segment(s.start, s.end, s.text.strip()) for s in segments]
        return TextResult(
            text=" ".join(s.text for s in segs),
            language=info.language,
            segments=segs,
            confidence=info.language_probability,
        )
