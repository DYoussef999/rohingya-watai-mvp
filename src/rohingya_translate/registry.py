"""Maps backend names in the config to classes. Add new backends here."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from rohingya_translate.config import StageConfig


def _echo(config: StageConfig) -> Any:
    from rohingya_translate.stages.echo import EchoBackend

    return EchoBackend(config)


def _whisper(config: StageConfig) -> Any:
    # Imported lazily so the package works without ML dependencies installed.
    from rohingya_translate.stages.whisper import WhisperBackend

    return WhisperBackend(config)


def _siglip(config: StageConfig) -> Any:
    from rohingya_translate.stages.siglip import SiglipBackend

    return SiglipBackend(config)


def _wav2vec2(config: StageConfig) -> Any:
    from rohingya_translate.stages.wav2vec2 import Wav2Vec2Embedder

    return Wav2Vec2Embedder(config)


def _demo(config: StageConfig) -> Any:
    from rohingya_translate.stages.demo import DemoBackend

    return DemoBackend(config)


def _windows(config: StageConfig) -> Any:
    from rohingya_translate.stages.windows_tts import WindowsSpeechBackend

    return WindowsSpeechBackend(config)


BACKENDS: dict[str, Callable[[StageConfig], Any]] = {
    "echo": _echo,
    "whisper": _whisper,
    "siglip": _siglip,
    "wav2vec2": _wav2vec2,
    "demo": _demo,
    "windows": _windows,
}


def create_backend(config: StageConfig, required: type) -> Any:
    """Build the backend named in ``config`` and check it implements ``required``."""
    try:
        factory = BACKENDS[config.backend]
    except KeyError:
        raise ValueError(
            f"unknown backend {config.backend!r}; choose from {sorted(BACKENDS)}"
        ) from None
    backend = factory(config)
    if not isinstance(backend, required):
        raise TypeError(f"backend {config.backend!r} does not implement {required.__name__}")
    return backend
