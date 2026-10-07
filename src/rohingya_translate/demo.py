"""Made-up demo data so every part of the app has something to show: ``demo.bat``.

Everything here is synthetic. The "recordings" are tone patterns, not voices,
and no Rohingya words are invented: entries only have English meanings. It all
lives in its own folder (``data/demo/``) with its own settings
(``configs/demo.toml``), so it never mixes with the real dictionary or ends up
in training data.
"""

from __future__ import annotations

import argparse
import csv
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from rohingya_translate.audio import Audio, save_wav
from rohingya_translate.config import Config, load_config
from rohingya_translate.lexicon import Lexicon
from rohingya_translate.stages.demo import CARD_COLOURS

DEMO_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "demo.toml"
CONSENT = "DEMO-NOT-REAL"

# meaning -> (speakers who "taught" it, whether a picture check agrees).
# Chosen so the dictionary shows every status.
TEACHING = {
    "water": (3, False),  # verified: three speakers agree
    "rice": (3, False),  # verified
    "doctor": (2, True),  # verified: two speakers plus a picture check
    "medicine": (2, False),  # corroborated: two speakers
    "fish": (1, True),  # corroborated: one speaker plus a picture check
    "house": (1, False),  # proposed: one speaker
    "child": (1, False),  # proposed
}
# Two speakers give the same-sounding word different meanings -> both disputed.
DISPUTE = [("pain", "DEMO-S01"), ("fever", "DEMO-S02")]
PHRASES = [
    "Where is the clinic?",
    "My child has a fever.",
    "I need clean water.",
    "Thank you for your help.",
    "How much does this cost?",
]


@dataclass
class DemoFiles:
    """Sample files the app pre-fills its forms with."""

    phrase: Path
    word: Path
    picture: Path | None


def _chord(index: int) -> list[float]:
    """Three tones unique to ``index``; the echo embedder tells these apart."""
    return [(band + 0.5) * 125.0 for band in (3 + index, 20 + index, 40 + index)]


def tone_clip(index: int, speaker: int = 0, seconds: float = 0.6) -> Audio:
    """A stand-in "recording": the same chord for every speaker, with their own volume and noise."""
    rng = np.random.default_rng(1000 * index + speaker)
    n = int(16_000 * (seconds + 0.05 * speaker))
    t = np.arange(n) / 16_000
    wave = sum(np.sin(2 * np.pi * f * t) for f in _chord(index)) / 3
    fade = np.minimum(1.0, np.minimum(t, t[-1] - t) / 0.03)
    samples = (0.3 + 0.03 * speaker) * wave * fade + 0.005 * rng.standard_normal(n)
    return Audio(samples.astype(np.float32))


def picture_card(meaning: str, size: int = 320) -> np.ndarray | None:
    """A coloured card with the word on it (RGB). None without OpenCV."""
    try:
        import cv2
    except ImportError:
        return None
    card = np.empty((size, size, 3), dtype=np.uint8)
    card[:] = CARD_COLOURS[meaning]
    dark = sum(CARD_COLOURS[meaning]) > 450
    ink = (30, 30, 30) if dark else (255, 255, 255)
    cv2.rectangle(card, (40, 40), (size - 40, size - 40), ink, 3)
    text = meaning.upper()
    scale = 1.4 if len(text) <= 6 else 1.0
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, 2)
    cv2.putText(card, text, ((size - w) // 2, (size + h) // 2), cv2.FONT_HERSHEY_DUPLEX,
                scale, ink, 2, cv2.LINE_AA)
    return card


def _save_png(image: np.ndarray, path: Path) -> None:
    import cv2

    ok, png = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if ok:
        path.write_bytes(png.tobytes())


def build_demo(config: Config, reset: bool = False) -> DemoFiles:
    """Write demo recordings, pictures, a phrasebook and a filled-in dictionary."""
    lexicon_dir = Path(config.lexicon.path)
    root = lexicon_dir.parent
    if reset and root.exists():
        try:
            shutil.rmtree(root)
        except PermissionError as e:
            raise RuntimeError("The demo is already open in another window. Close it first, "
                               "then open the demo again.") from e
    recordings, prompts = root / "recordings", root / "prompts"
    recordings.mkdir(parents=True, exist_ok=True)
    prompts.mkdir(parents=True, exist_ok=True)

    # One chord per spoken form; "pain"/"fever" share one on purpose.
    chords = {meaning: i for i, meaning in enumerate([*TEACHING, "pain"])}
    chords["fever"] = chords["pain"]

    phrasebook = Path(config.speech_translator.options.get(
        "phrasebook", root / "phrasebook.csv"))
    with open(phrasebook, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "english"])
        for i, english in enumerate(PHRASES):
            name = f"recordings/phrase_{i + 1}.wav"
            save_wav(tone_clip(len(chords) + i, seconds=1.6), root / name)
            writer.writerow([name, english])
        for meaning in TEACHING:
            name = f"recordings/word_{meaning}.wav"
            save_wav(tone_clip(chords[meaning], speaker=7), root / name)
            writer.writerow([name, meaning])

    for meaning in CARD_COLOURS:
        card = picture_card(meaning)
        if card is not None:
            _save_png(card, prompts / f"{meaning}.png")

    if (lexicon_dir / "lexicon.db").exists():
        try:
            (lexicon_dir / "lexicon.db").unlink()
        except PermissionError as e:
            raise RuntimeError("The demo is already open in another window. Close it first, "
                               "then open the demo again.") from e
    shutil.rmtree(lexicon_dir / "clips", ignore_errors=True)
    lex = Lexicon.open(config, vision=True)
    try:
        for meaning, (speakers, picture_agrees) in TEACHING.items():
            for s in range(speakers):
                result = lex.teach(tone_clip(chords[meaning], speaker=s), meaning,
                                   speaker_id=f"DEMO-S{s + 1:02d}", consent_id=CONSENT,
                                   dialect_region="(demo)")
            card = picture_card(meaning) if picture_agrees else None
            if card is not None:
                lex.check_image(result.entry.id, card)
        for meaning, speaker in DISPUTE:
            lex.teach(tone_clip(chords[meaning], speaker=int(speaker[-1])), meaning,
                      speaker_id=speaker, consent_id=CONSENT, dialect_region="(demo)")
    finally:
        lex.close()

    picture = prompts / "water.png"
    return DemoFiles(root / "recordings" / "phrase_3.wav", root / "recordings" / "word_water.wav",
                     picture if picture.exists() else None)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create made-up demo data for the app.")
    parser.add_argument("--config", default=str(DEMO_CONFIG), help="demo settings file")
    args = parser.parse_args(argv)
    files = build_demo(load_config(args.config), reset=True)
    print(f"Demo data written next to {files.phrase.parent}")


if __name__ == "__main__":
    main()
