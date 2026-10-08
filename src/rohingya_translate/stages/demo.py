"""Demo-only stand-ins, for showing the app with the made-up data from ``demo.py``.

- ``translate_speech`` looks a clip up in a phrasebook of demo recordings.
- ``label_image`` recognises the demo picture cards by their background colour.

Neither understands real speech or real photos.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from rohingya_translate.audio import Audio, load_wav
from rohingya_translate.config import StageConfig
from rohingya_translate.stages.base import Label, Segment, TextResult
from rohingya_translate.stages.echo import EchoBackend

# Every word that gets a demo picture card, grouped by theme.
CARD_WORDS = (
    "water", "rice", "fish", "bread", "fruit", "vegetables", "egg", "tea", "milk", "salt",
    "doctor", "medicine", "hospital", "nurse", "bandage", "injection", "pain", "cold",
    "mother", "father", "child", "baby", "brother", "sister", "grandmother",
    "house", "tent", "door", "bed", "blanket", "cooking pot", "soap", "bucket",
    "chicken", "cow", "goat", "rain", "sun", "tree",
    "boat", "road", "money", "phone", "book", "shoes",
)


def _card_colour(index: int, count: int) -> tuple[int, int, int]:
    """Evenly spread hues, alternating light and deep, so every card looks different."""
    import colorsys

    light = 0.62 if index % 2 == 0 else 0.42
    r, g, b = colorsys.hls_to_rgb((0.58 + index / count) % 1.0, light, 0.62)  # water: blue
    return round(r * 255), round(g * 255), round(b * 255)


# Background colour (RGB) of each demo picture card; the demo labeler recognises these.
CARD_COLOURS: dict[str, tuple[int, int, int]] = {
    word: _card_colour(i, len(CARD_WORDS)) for i, word in enumerate(CARD_WORDS)
}
PHRASE_MATCH = 0.9  # echo-embedding similarity needed to count as a phrasebook hit


class DemoBackend:
    """Implements SpeechTranslator and ImageLabeler for the demo data only."""

    def __init__(self, config: StageConfig | None = None) -> None:
        self.config = config or StageConfig()
        self.name = "demo"
        self._echo = EchoBackend()
        self._phrases: list[tuple[np.ndarray, str]] | None = None

    def translate_speech(self, audio: Audio) -> TextResult:
        phrases = self._phrasebook()
        if not phrases:
            return TextResult("(no demo phrasebook found; run demo.bat)", "en", confidence=0.0)
        vector = self._echo.embed(audio)
        similarity, english = max((float(v @ vector), e) for v, e in phrases)
        if similarity < PHRASE_MATCH:
            return TextResult("(not one of the demo recordings)", "en", confidence=0.0)
        return TextResult(english, "en", [Segment(0.0, audio.duration, english)], similarity)

    def label_image(self, image: np.ndarray, candidates: list[str]) -> list[Label]:
        background = _border_colour(image)
        labels = []
        for c in candidates:
            colour = CARD_COLOURS.get(c)
            distance = np.linalg.norm(background - colour) if colour else np.inf
            labels.append(Label(c, float(max(0.0, 1.0 - distance / 60))))
        return sorted(labels, key=lambda label: label.score, reverse=True)

    def _phrasebook(self) -> list[tuple[np.ndarray, str]]:
        if self._phrases is None:
            path = Path(self.config.options.get("phrasebook", "data/demo/phrasebook.csv"))
            self._phrases = []
            if path.is_file():
                with open(path, encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        clip = load_wav(path.parent / row["path"])
                        self._phrases.append((self._echo.embed(clip), row["english"]))
        return self._phrases


def _border_colour(image: np.ndarray) -> np.ndarray:
    """Mean colour of the outer edge, where a picture card shows its background."""
    h, w = image.shape[:2]
    edge = max(1, min(h, w) // 12)
    border = np.concatenate([
        image[:edge].reshape(-1, 3), image[-edge:].reshape(-1, 3),
        image[:, :edge].reshape(-1, 3), image[:, -edge:].reshape(-1, 3),
    ])
    return border.astype(np.float32).mean(axis=0)
