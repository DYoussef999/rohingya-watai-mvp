import wave

import numpy as np

from rohingya_translate.audio import SAMPLE_RATE, load_wav, resample


def write_wav(path, samples: np.ndarray, rate: int, channels: int = 1) -> None:
    with wave.open(str(path), "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes((samples * 32767).astype(np.int16).tobytes())


def test_load_wav_downmixes_and_resamples(tmp_path):
    stereo = np.zeros(44_100 * 2, dtype=np.float32)  # 1 s of interleaved stereo
    write_wav(tmp_path / "a.wav", stereo, rate=44_100, channels=2)

    audio = load_wav(tmp_path / "a.wav")

    assert audio.sample_rate == SAMPLE_RATE
    assert audio.samples.ndim == 1
    assert abs(audio.duration - 1.0) < 1e-3


def test_resample_keeps_same_rate_untouched():
    samples = np.linspace(-1, 1, 100, dtype=np.float32)
    assert np.array_equal(resample(samples, 16_000, 16_000), samples)
