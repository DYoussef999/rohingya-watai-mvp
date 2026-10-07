import csv

import numpy as np
import pytest

from rohingya_translate.audio import Audio, trim_silence
from rohingya_translate.config import Config, LexiconConfig
from rohingya_translate.lexicon import (
    Lexicon,
    LexiconStore,
    Status,
    Support,
    decide,
    load_vocabulary,
    meaning_from_prompt,
)
from rohingya_translate.lexicon_cli import main as rlexicon
from rohingya_translate.stages.base import Label
from rohingya_translate.stages.echo import EchoBackend

PHOTO = np.zeros((8, 8, 3), dtype=np.uint8)


def tone(hz: float, seconds: float = 0.5) -> Audio:
    """Stands in for a spoken word: the echo embedder tells tones apart by pitch."""
    t = np.arange(int(16_000 * seconds)) / 16_000
    return Audio((0.5 * np.sin(2 * np.pi * hz * t)).astype(np.float32))


WATER, RAIN = tone(440), tone(1_500)


class FakeLabeler:
    """Sees whatever it is told to see."""

    def __init__(self, sees: str) -> None:
        self.sees = sees

    def label_image(self, image, candidates):
        labels = [Label(c, 0.9 if c == self.sees else 0.05) for c in candidates]
        return sorted(labels, key=lambda label: label.score, reverse=True)


@pytest.fixture
def make_lexicon(tmp_path):
    lexicons = []

    def make(sees: str | None = None, **settings) -> Lexicon:
        settings.setdefault("vocabulary", str(tmp_path / "missing.txt"))
        lex = Lexicon(
            LexiconStore(tmp_path / "lexicon"), EchoBackend(), "echo:echo",
            LexiconConfig(**settings), FakeLabeler(sees) if sees else None, "fake",
        )
        lexicons.append(lex)
        return lex

    yield make
    for lex in lexicons:
        lex.close()


def teach(lex: Lexicon, audio: Audio, meaning: str, speaker: str, **kwargs):
    return lex.teach(audio, meaning, speaker_id=speaker, consent_id=f"C-{speaker}", **kwargs)


# Policy


def test_vision_alone_never_verifies():
    assert decide(Support(speakers=1, vision=True, conflicts=0)) == Status.CORROBORATED
    assert decide(Support(speakers=0, vision=True, conflicts=0)) == Status.PROPOSED


def test_vision_can_replace_one_speaker():
    assert decide(Support(speakers=2, vision=False, conflicts=0)) == Status.CORROBORATED
    assert decide(Support(speakers=2, vision=True, conflicts=0)) == Status.VERIFIED
    assert decide(Support(speakers=3, vision=False, conflicts=0)) == Status.VERIFIED


def test_disagreement_blocks_verification():
    assert decide(Support(speakers=3, vision=True, conflicts=2)) == Status.DISPUTED
    assert decide(Support(speakers=4, vision=False, conflicts=1)) == Status.VERIFIED


# Teaching and agreement


def test_three_speakers_agreeing_verify_an_entry(make_lexicon):
    lex = make_lexicon()
    first = teach(lex, WATER, "Water", "S1")
    assert first.new_entry and first.entry.status == Status.PROPOSED
    teach(lex, WATER, "water ", "S2")
    result = teach(lex, WATER, "water", "S3")

    assert not result.new_entry
    assert result.entry.id == first.entry.id
    assert result.entry.status == Status.VERIFIED


def test_same_speaker_repeating_does_not_count_twice(make_lexicon):
    lex = make_lexicon()
    for _ in range(3):
        result = teach(lex, WATER, "water", "S1")
    assert result.entry.support.speakers == 1
    assert result.entry.status == Status.PROPOSED


def test_camera_check_stands_in_for_one_speaker(make_lexicon):
    lex = make_lexicon(sees="water")
    teach(lex, WATER, "water", "S1")
    result = teach(lex, WATER, "water", "S2", image=PHOTO)

    assert result.vision.agrees
    assert result.entry.status == Status.VERIFIED


def test_camera_check_that_disagrees_adds_nothing(make_lexicon):
    lex = make_lexicon(sees="rain")
    teach(lex, RAIN, "rain", "S9")
    result = teach(lex, WATER, "water", "S1", image=PHOTO)

    assert not result.vision.agrees and result.vision.top_label == "rain"
    assert result.entry.status == Status.PROPOSED


def test_conflicting_meanings_are_disputed(make_lexicon):
    lex = make_lexicon()
    teach(lex, WATER, "water", "S1")
    result = teach(lex, WATER, "rain", "S2")

    assert result.new_entry
    assert [e.meaning for e in result.conflicts] == ["water"]
    assert {e.meaning: e.status for e in lex.entries()} == {
        "water": Status.DISPUTED, "rain": Status.DISPUTED,
    }


def test_one_speaker_giving_two_senses_is_not_a_dispute(make_lexicon):
    lex = make_lexicon()
    teach(lex, WATER, "water", "S1")
    teach(lex, WATER, "rain", "S1")
    assert all(e.status == Status.PROPOSED for e in lex.entries())


def test_different_sounds_with_same_meaning_stay_separate(make_lexicon):
    lex = make_lexicon()
    teach(lex, WATER, "water", "S1")
    result = teach(lex, RAIN, "water", "S2")  # a synonym or dialect word
    assert result.new_entry
    assert len(lex.entries()) == 2


def test_spelling_is_filled_but_never_overwritten(make_lexicon):
    lex = make_lexicon()
    teach(lex, WATER, "water", "S1", rohingyalish="fani")
    result = teach(lex, WATER, "water", "S2", rohingyalish="pani")
    assert result.entry.rohingyalish == "fani"


def test_teach_requires_speaker_and_consent(make_lexicon):
    lex = make_lexicon()
    with pytest.raises(ValueError, match="consent"):
        lex.teach(WATER, "water", speaker_id="S1", consent_id="")


# Looking up and reading back


def test_lookup_finds_the_word_by_sound(make_lexicon):
    lex = make_lexicon()
    teach(lex, WATER, "water", "S1")
    teach(lex, RAIN, "rain", "S1")

    best = lex.lookup(WATER)[0]
    assert best.entry.meaning == "water" and best.confident
    assert not lex.lookup(tone(3_000))[0].confident


def test_vectors_from_another_embedder_are_ignored(make_lexicon):
    lex = make_lexicon()
    teach(lex, WATER, "water", "S1")
    lex.embedder_id = "wav2vec2:other-model"
    assert lex.lookup(WATER) == []
    assert lex.reembed() == 1
    assert lex.lookup(WATER)[0].confident


def test_lexicon_survives_reopening(make_lexicon):
    teach(make_lexicon(), WATER, "water", "S1")
    assert [e.meaning for e in make_lexicon().entries()] == ["water"]


def test_suggest_ranks_known_meanings(make_lexicon, tmp_path):
    vocab = tmp_path / "vocab.txt"
    vocab.write_text("# comment\nwater\nRice\n\n", encoding="utf-8")
    assert load_vocabulary(vocab) == ["water", "rice"]

    lex = make_lexicon(sees="rice", vocabulary=str(vocab))
    assert lex.suggest(PHOTO)[0].text == "rice"


def test_export_writes_only_verified_clips(make_lexicon, tmp_path):
    lex = make_lexicon()
    for speaker in ("S1", "S2", "S3"):
        teach(lex, WATER, "water", speaker, dialect_region="Maungdaw")
    teach(lex, RAIN, "rain", "S1")

    out = tmp_path / "clips.csv"
    assert lex.export_csv(out) == 3
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert {r["english"] for r in rows} == {"water"}
    assert {r["dialect_region"] for r in rows} == {"Maungdaw"}


def test_prompt_file_name_is_the_meaning():
    assert meaning_from_prompt("data/prompts/Cooking_Pot.jpg") == "cooking pot"


def test_trim_silence_cuts_quiet_ends():
    quiet = np.zeros(8_000, dtype=np.float32)
    padded = Audio(np.concatenate([quiet, WATER.samples, quiet]))
    assert abs(trim_silence(padded).duration - WATER.duration) < 0.05


# Settings and command line


def test_lexicon_settings_load_and_typos_are_rejected():
    assert Config.from_dict({"lexicon": {"min_speakers": 5}}).lexicon.min_speakers == 5
    with pytest.raises(ValueError, match="unknown"):
        Config.from_dict({"lexicon": {"min_speaker": 5}})


def test_cli_teach_and_list(tmp_path, capsys):
    from rohingya_translate.audio import save_wav

    config = tmp_path / "config.toml"
    config.write_text(f'[lexicon]\npath = "{(tmp_path / "lex").as_posix()}"\n', encoding="utf-8")
    clip = tmp_path / "water.wav"
    save_wav(WATER, clip)

    rlexicon(["--config", str(config), "teach", str(clip), "--meaning", "water",
              "--speaker", "S1", "--consent", "C1"])
    rlexicon(["--config", str(config), "list"])
    out = capsys.readouterr().out
    assert "New entry" in out and "#1 water: proposed" in out


def test_exposure_settles_only_when_brightness_is_steady():
    from rohingya_translate.images import exposure_settled

    assert not exposure_settled([210, 106, 74, 78, 81])  # camera still adjusting
    assert not exposure_settled([82, 82])  # too few frames to tell
    assert exposure_settled([210, 106, 81, 82, 84, 82, 83])


def test_placeholder_image_model_is_flagged(make_lexicon):
    assert not make_lexicon(sees="water").vision_is_placeholder
    lex = make_lexicon()
    lex.labeler, lex.labeler_id = EchoBackend(), "echo:echo"
    assert lex.vision_is_placeholder


def test_prompt_pictures_are_found_by_meaning(tmp_path):
    from rohingya_translate.lexicon import list_prompts

    for name in ("cooking_pot.jpg", "Water.PNG", "notes.txt"):
        (tmp_path / name).write_bytes(b"")
    found = list_prompts(tmp_path)
    assert set(found) == {"cooking pot", "water"}
    assert list_prompts(tmp_path / "missing") == {}
