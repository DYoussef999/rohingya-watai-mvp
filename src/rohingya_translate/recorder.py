"""Microphone recording and playback via sounddevice (MIT; bundles PortAudio, MIT-style).

Recordings stay in memory; nothing is written to disk unless the caller saves it.
"""

from __future__ import annotations

import time

import numpy as np

from rohingya_translate.audio import SAMPLE_RATE, Audio

MAX_SECONDS = 60  # stop runaway recordings


def _sd():
    try:
        import sounddevice
    except (ImportError, OSError) as e:
        raise RuntimeError(
            'Recording needs the sounddevice package: pip install -e "."') from e
    return sounddevice


class Recorder:
    """Records the default microphone at 16 kHz mono. ``level`` is the latest loudness (0-1)."""

    def __init__(self) -> None:
        self._stream = None
        self._chunks: list[np.ndarray] = []
        self._started = 0.0
        self.level = 0.0

    @property
    def recording(self) -> bool:
        return self._stream is not None

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._started if self.recording else 0.0

    def start(self) -> None:
        sd = _sd()
        self._chunks, self.level = [], 0.0
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=self._callback)
            self._stream.start()
        except Exception as e:
            self._stream = None
            raise RuntimeError(
                "The microphone could not be opened. Check it is plugged in, and that "
                "Windows Settings > Privacy & security > Microphone allows desktop apps."
            ) from e
        self._started = time.monotonic()

    def stop(self) -> Audio:
        """Stop and return what was recorded."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.level = 0.0
        samples = np.concatenate(self._chunks) if self._chunks else np.zeros(0, np.float32)
        return Audio(samples.astype(np.float32))

    def _callback(self, indata, frames, time_info, status) -> None:  # audio thread
        if self.elapsed > MAX_SECONDS:
            return
        mono = indata[:, 0].copy()
        self._chunks.append(mono)
        # Speech RMS is roughly 0.01-0.2; scale so normal talking fills most of the meter.
        self.level = float(min(1.0, np.sqrt(np.mean(mono**2)) * 8))


def play(audio: Audio) -> None:
    """Play without blocking. Starting another sound stops this one."""
    sd = _sd()
    sd.stop()
    if len(audio.samples):
        sd.play(audio.samples, audio.sample_rate)


def stop_playback() -> None:
    try:
        _sd().stop()
    except RuntimeError:
        pass
