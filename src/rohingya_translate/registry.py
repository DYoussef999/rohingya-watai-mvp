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


BACKENDS: dict[str, Callable[[StageConfig], Any]] = {
    "echo": _echo,
    "whisper": _whisper,
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
