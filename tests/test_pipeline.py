import numpy as np
import pytest

from rohingya_translate.audio import Audio
from rohingya_translate.config import Config, StageConfig, load_config
from rohingya_translate.pipeline import Pipeline
from rohingya_translate.registry import create_backend
from rohingya_translate.stages.base import SpeechTranslator

TWO_SECONDS = Audio(np.zeros(32_000, dtype=np.float32))


def test_default_config_loads():
    config = load_config()
    assert config.mode == "direct"
    assert config.speech_translator.backend == "echo"


def test_unknown_config_keys_become_options():
    stage = StageConfig.from_dict({"backend": "whisper", "beam_size": 3})
    assert stage.options == {"beam_size": 3}


def test_bad_mode_is_rejected():
    with pytest.raises(ValueError):
        Config.from_dict({"pipeline": {"mode": "telepathy"}})


def test_direct_mode():
    result = Pipeline(Config(mode="direct")).run(TWO_SECONDS)
    assert result.english.language == "en"
    assert result.transcript is None
    assert "2.0s" in result.english.text


def test_cascade_mode_keeps_transcript():
    result = Pipeline(Config(mode="cascade")).run(TWO_SECONDS)
    assert result.transcript is not None
    assert result.transcript.language == "rhg"
    assert result.english.text.startswith("[en]")


def test_synthesizer_is_optional():
    assert Pipeline(Config()).run(TWO_SECONDS).speech is None
    assert Pipeline(Config(synthesizer="echo")).run(TWO_SECONDS).speech is not None


def test_unknown_backend_is_rejected():
    with pytest.raises(ValueError, match="unknown backend"):
        create_backend(StageConfig(backend="nope"), SpeechTranslator)


def test_voice_settings_load():
    config = Config.from_dict({"pipeline": {"synthesizer": "windows", "read_aloud": False},
                               "synthesizer": {"voice": "Zira", "rate": 2}})
    assert config.voice.backend == "windows"
    assert config.voice.options == {"voice": "Zira", "rate": 2}
    assert config.read_aloud is False


def test_speak_false_skips_the_voice():
    pipeline = Pipeline(Config(synthesizer="echo"))
    assert pipeline.run(TWO_SECONDS, speak=False).speech is None


@pytest.mark.skipif(__import__("sys").platform != "win32", reason="Windows voices only")
def test_windows_voice_reads_text_aloud():
    from rohingya_translate.stages.windows_tts import WindowsSpeechBackend

    audio = WindowsSpeechBackend().synthesize("I need clean water.")
    assert audio.sample_rate == 16_000
    assert audio.duration > 0.5
    assert WindowsSpeechBackend().synthesize("  ").duration == 0
