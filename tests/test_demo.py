from rohingya_translate.audio import load_wav
from rohingya_translate.config import load_config
from rohingya_translate.demo import DEMO_CONFIG, PHRASES, build_demo
from rohingya_translate.lexicon import Lexicon, Status
from rohingya_translate.stages.demo import DemoBackend


def demo_config(tmp_path):
    config = load_config(DEMO_CONFIG)
    config.lexicon.path = str(tmp_path / "demo" / "lexicon")
    config.speech_translator.options["phrasebook"] = str(tmp_path / "demo" / "phrasebook.csv")
    return config


def test_demo_dictionary_shows_every_status(tmp_path):
    config = demo_config(tmp_path)
    build_demo(config)

    lex = Lexicon.open(config)
    try:
        status = {e.meaning: e.status for e in lex.entries()}
    finally:
        lex.close()
    assert status["water"] == Status.VERIFIED
    assert status["doctor"] == Status.VERIFIED  # two speakers + picture check
    assert status["medicine"] == Status.CORROBORATED
    assert status["fish"] == Status.CORROBORATED  # one speaker + picture check
    assert status["house"] == Status.PROPOSED
    assert status["pain"] == status["fever"] == Status.DISPUTED


def test_demo_phrasebook_translates_demo_recordings(tmp_path):
    config = demo_config(tmp_path)
    files = build_demo(config)

    translator = DemoBackend(config.speech_translator)
    assert translator.translate_speech(load_wav(files.phrase)).text == PHRASES[2]
    assert translator.translate_speech(load_wav(files.word)).text == "water"


def test_demo_rebuild_starts_fresh(tmp_path):
    config = demo_config(tmp_path)
    build_demo(config)
    build_demo(config, reset=True)
    lex = Lexicon.open(config)
    try:
        assert len(lex.entries()) == 9
    finally:
        lex.close()
