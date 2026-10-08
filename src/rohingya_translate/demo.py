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
import random
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from rohingya_translate.audio import Audio, save_wav
from rohingya_translate.config import Config, load_config
from rohingya_translate.lexicon import Lexicon
from rohingya_translate.stages.demo import CARD_COLOURS

DEMO_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "demo.toml"
CONSENT = "DEMO-NOT-REAL"
SPEAKERS = [f"DEMO-S{i:02d}" for i in range(1, 7)]
NEW_SPEAKER = "DEMO-S07"  # pre-filled on the Teach tab, so saving adds a new voice

# meaning -> (speakers who "taught" it, whether a picture check agrees).
# 3 speakers -> verified; 2 + picture -> verified; 2, or 1 + picture -> likely; 1 -> new.
TEACHING: dict[str, tuple[int, bool]] = {
    # food and water
    "water": (3, False), "rice": (3, False), "fish": (1, True), "bread": (2, False),
    "fruit": (3, False), "vegetables": (1, False), "egg": (2, True), "tea": (3, False),
    "milk": (1, False), "salt": (2, False),
    # health
    "doctor": (2, True), "medicine": (2, False), "hospital": (3, False), "nurse": (1, True),
    "bandage": (2, False), "injection": (1, False),
    # family
    "mother": (3, False), "father": (3, False), "child": (1, False), "baby": (2, True),
    "brother": (2, False), "sister": (1, False), "grandmother": (3, False),
    # home
    "house": (1, False), "tent": (2, True), "door": (1, False), "bed": (3, False),
    "blanket": (2, False), "cooking pot": (1, False), "soap": (3, False), "bucket": (2, False),
    # animals and nature
    "chicken": (2, False), "cow": (3, False), "goat": (1, False), "rain": (2, True),
    "sun": (3, False), "tree": (1, False),
    # travel and things
    "boat": (3, False), "road": (1, False), "money": (2, True), "phone": (1, False),
    "book": (2, False), "shoes": (3, False),
}
# Pairs where two speakers gave the same-sounding word different meanings -> both "unclear".
DISPUTES = [("pain", "fever"), ("cold", "winter")]
PHRASES = [
    "Where is the clinic?",
    "My child has a fever.",
    "I need clean water.",
    "Thank you for your help.",
    "How much does this cost?",
    "I have pain here.",
    "Where can I get food?",
    "My mother is sick.",
    "Please speak slowly.",
    "I don't understand.",
    "When is the doctor coming?",
    "We need blankets for the night.",
    "I lost my documents.",
    "Is this water safe to drink?",
    "Can you help my family?",
]


@dataclass
class DemoFiles:
    """Sample files the app pre-fills its forms with."""

    phrase: Path
    word: Path
    picture: Path | None
    phrases: list[Path] = field(default_factory=list)


def chords(count: int, seed: int = 7) -> list[tuple[int, int, int]]:
    """``count`` sets of three frequency bands, no two sharing more than one band.

    The echo embedder compares sound band by band, so this keeps every demo
    "word" clearly distinct from every other.
    """
    rng = random.Random(seed)
    chosen: list[tuple[int, int, int]] = []
    while len(chosen) < count:
        candidate = tuple(sorted(rng.sample(range(2, 62), 3)))
        if all(len(set(candidate) & set(c)) <= 1 for c in chosen):
            chosen.append(candidate)
    return chosen


def tone_clip(bands: tuple[int, ...], speaker: int = 0, seconds: float = 0.6) -> Audio:
    """A stand-in "recording": the same chord for every speaker, with their own volume and noise."""
    rng = np.random.default_rng(sum(bands) * 1000 + speaker)
    n = int(16_000 * (seconds + 0.05 * (speaker % 4)))
    t = np.arange(n) / 16_000
    wave = sum(np.sin(2 * np.pi * (b + 0.5) * 125.0 * t) for b in bands) / len(bands)
    fade = np.minimum(1.0, np.minimum(t, t[-1] - t) / 0.03)
    samples = (0.3 + 0.03 * (speaker % 5)) * wave * fade + 0.005 * rng.standard_normal(n)
    return Audio(samples.astype(np.float32))


def picture_card(meaning: str, size: int = 320) -> np.ndarray | None:
    """A coloured card with the word on it (RGB). None without OpenCV."""
    try:
        import cv2
    except ImportError:
        return None
    colour = CARD_COLOURS[meaning]
    card = np.empty((size, size, 3), dtype=np.uint8)
    card[:] = colour
    ink = (25, 25, 30) if sum(colour) > 420 else (255, 255, 255)
    cv2.rectangle(card, (40, 40), (size - 40, size - 40), ink, 3)
    text = meaning.upper()
    scale = 1.4
    while cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, 2)[0][0] > size - 100:
        scale -= 0.1  # shrink long words to fit inside the frame
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, 2)
    cv2.putText(card, text, ((size - w) // 2, (size + h) // 2), cv2.FONT_HERSHEY_DUPLEX,
                scale, ink, 2, cv2.LINE_AA)
    return card


def _save_png(image: np.ndarray, path: Path) -> None:
    import cv2

    ok, png = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if ok:
        path.write_bytes(png.tobytes())


def _clear(path: Path) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    except PermissionError as e:
        raise RuntimeError("The demo is already open in another window. Close it first, "
                           "then open the demo again.") from e


def build_demo(config: Config, reset: bool = False) -> DemoFiles:
    """Write demo recordings, pictures, a phrasebook and a filled-in dictionary."""
    lexicon_dir = Path(config.lexicon.path)
    root = lexicon_dir.parent
    if reset:
        _clear(root)
    recordings, prompts = root / "recordings", root / "prompts"
    recordings.mkdir(parents=True, exist_ok=True)
    prompts.mkdir(parents=True, exist_ok=True)

    # One distinct sound per spoken word (each dispute pair shares one) and per phrase.
    spoken = [*TEACHING, *(first for first, _ in DISPUTES)]
    pool = chords(len(spoken) + len(PHRASES))
    sound = dict(zip(spoken, pool))
    for first, second in DISPUTES:
        sound[second] = sound[first]
    phrase_sounds = pool[len(spoken):]

    phrasebook = Path(config.speech_translator.options.get(
        "phrasebook", root / "phrasebook.csv"))
    phrase_files = []
    with open(phrasebook, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "english"])
        for i, (english, bands) in enumerate(zip(PHRASES, phrase_sounds)):
            name = f"recordings/phrase_{i + 1:02d}.wav"
            save_wav(tone_clip(bands, seconds=1.6), root / name)
            writer.writerow([name, english])
            phrase_files.append(root / name)
        for meaning in TEACHING:
            name = f"recordings/word_{meaning.replace(' ', '_')}.wav"
            save_wav(tone_clip(sound[meaning], speaker=9), root / name)
            writer.writerow([name, meaning])

    for meaning in CARD_COLOURS:
        card = picture_card(meaning)
        if card is not None:
            _save_png(card, prompts / f"{meaning.replace(' ', '_')}.png")

    _clear(lexicon_dir)
    lex = Lexicon.open(config, vision=True)
    try:
        for n, (meaning, (count, picture_agrees)) in enumerate(TEACHING.items()):
            for k in range(count):
                speaker = (n + k) % len(SPEAKERS)  # spread the work over all speakers
                result = lex.teach(tone_clip(sound[meaning], speaker=speaker), meaning,
                                   speaker_id=SPEAKERS[speaker], consent_id=CONSENT,
                                   dialect_region="(demo)")
            card = picture_card(meaning) if picture_agrees else None
            if card is not None:
                lex.check_image(result.entry.id, card)
        for first, second in DISPUTES:
            for speaker, meaning in ((0, first), (1, second)):
                lex.teach(tone_clip(sound[meaning], speaker=speaker), meaning,
                          speaker_id=SPEAKERS[speaker], consent_id=CONSENT,
                          dialect_region="(demo)")
    finally:
        lex.close()

    picture = prompts / "water.png"
    return DemoFiles(phrase_files[2], recordings / "word_water.wav",
                     picture if picture.exists() else None, phrase_files)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create made-up demo data for the app.")
    parser.add_argument("--config", default=str(DEMO_CONFIG), help="demo settings file")
    args = parser.parse_args(argv)
    files = build_demo(load_config(args.config), reset=True)
    print(f"Demo data written next to {files.phrase.parent}")


if __name__ == "__main__":
    main()
