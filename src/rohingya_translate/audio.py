"""Audio loading. Every stage receives the same format: mono float32 at 16 kHz."""

from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16_000


@dataclass(frozen=True)
class Audio:
    """Mono float32 samples in [-1, 1] at ``sample_rate`` Hz."""

    samples: np.ndarray
    sample_rate: int = SAMPLE_RATE

    @property
    def duration(self) -> float:
        """Length in seconds."""
        return len(self.samples) / self.sample_rate


def load_wav(path: str | Path) -> Audio:
    """Read a 16-bit PCM WAV file, downmix to mono and resample to 16 kHz.

    Other formats (mp3, m4a from a phone) need ffmpeg; convert them first with
    ``ffmpeg -i in.m4a -ar 16000 -ac 1 out.wav``.
    """
    with wave.open(str(path), "rb") as f:
        if f.getsampwidth() != 2:
            raise ValueError(f"{path}: only 16-bit PCM WAV is supported")
        rate = f.getframerate()
        channels = f.getnchannels()
        raw = f.readframes(f.getnframes())

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return Audio(resample(samples, rate, SAMPLE_RATE))


def resample(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Linear-interpolation resampling. Good enough for speech models."""
    if src_rate == dst_rate or len(samples) == 0:
        return samples.astype(np.float32)
    n_out = round(len(samples) * dst_rate / src_rate)
    src_t = np.arange(len(samples)) / src_rate
    dst_t = np.arange(n_out) / dst_rate
    return np.interp(dst_t, src_t, samples).astype(np.float32)
