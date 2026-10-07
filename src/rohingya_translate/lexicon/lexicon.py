"""The self-growing dictionary: teach words, match recordings, check meanings with images."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from rohingya_translate.audio import Audio, load_wav, trim_silence
from rohingya_translate.config import Config, LexiconConfig, StageConfig
from rohingya_translate.lexicon.policy import Status, Support, decide
from rohingya_translate.lexicon.store import EntryRow, LexiconStore, normalise_meaning
from rohingya_translate.registry import create_backend
from rohingya_translate.stages.base import AudioEmbedder, ImageLabeler, Label


@dataclass
class Entry:
    """A spoken word, its meaning, and how much that meaning is trusted."""

    id: int
    meaning: str
    rohingyalish: str
    hanifi: str
    status: Status
    support: Support


@dataclass
class Match:
    """A lexicon entry that sounds like a recording."""

    entry: Entry
    similarity: float
    confident: bool  # similarity is above the configured match threshold


@dataclass
class VisionCheck:
    """What the image model made of a photo, for one entry."""

    score: float  # score for the entry's meaning
    top_label: str
    agrees: bool


@dataclass
class TeachResult:
    entry: Entry
    new_entry: bool  # False when the recording joined an existing entry
    conflicts: list[Entry]  # same-sounding entries that were given other meanings
    vision: VisionCheck | None = None


def meaning_from_prompt(path: str | Path) -> str:
    """Prompt images are named after what they show: ``data/prompts/cooking_pot.jpg``."""
    return normalise_meaning(Path(path).stem.replace("_", " ").replace("-", " "))


IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")


def list_prompts(folder: str | Path) -> dict[str, Path]:
    """Prompt pictures in ``folder`` by meaning (from their file names). Missing folder -> {}."""
    folder = Path(folder)
    if not folder.is_dir():
        return {}
    files = sorted(f for f in folder.iterdir() if f.suffix.lower() in IMAGE_SUFFIXES)
    return {meaning_from_prompt(f): f for f in files}


def load_vocabulary(path: str | Path) -> list[str]:
    """Labels for camera checks, one per line; ``#`` starts a comment. Missing file -> []."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    return [normalise_meaning(s) for s in lines if s.strip() and not s.lstrip().startswith("#")]


class Lexicon:
    """Grows from recordings, checks itself with images, and only trusts agreement.

    Every recording is one speaker vouching for a meaning. Recordings that sound
    alike (by the audio embedder) are grouped into one entry; if speakers give
    the same-sounding word different meanings, the entries are marked disputed.
    Statuses are worked out on every read, so they always reflect the current
    thresholds and evidence.
    """

    def __init__(
        self,
        store: LexiconStore,
        embedder: AudioEmbedder,
        embedder_id: str,
        settings: LexiconConfig | None = None,
        labeler: ImageLabeler | None = None,
        labeler_id: str = "",
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.embedder_id = embedder_id
        self.settings = settings or LexiconConfig()
        self.labeler = labeler
        self.labeler_id = labeler_id

    @classmethod
    def open(cls, config: Config, vision: bool = False) -> Lexicon:
        """Build from settings. The image model is only loaded when ``vision`` is set."""
        embedder = create_backend(config.audio_embedder, AudioEmbedder)
        lexicon = cls(
            LexiconStore(config.lexicon.path),
            embedder,
            _backend_id(config.audio_embedder.backend, embedder),
            config.lexicon,
        )
        if vision:
            lexicon.load_labeler(config.image_labeler)
        return lexicon

    def load_labeler(self, stage: StageConfig) -> None:
        """Load the image model (slow the first time, so only done when photos are used)."""
        self.labeler = create_backend(stage, ImageLabeler)
        self.labeler_id = _backend_id(stage.backend, self.labeler)

    @property
    def vision_is_placeholder(self) -> bool:
        """True when the image model is a stand-in (``echo`` or ``demo``), not a real one."""
        return self.labeler_id.startswith(("echo:", "demo:"))

    def close(self) -> None:
        self.store.close()

    # Growing

    def teach(
        self,
        audio: Audio,
        meaning: str,
        *,
        speaker_id: str,
        consent_id: str,
        dialect_region: str = "",
        rohingyalish: str = "",
        hanifi: str = "",
        source: str = "teach",
        image: np.ndarray | None = None,
    ) -> TeachResult:
        """Add one speaker's recording of a word and what it means.

        Joins the best-matching entry with the same meaning, or starts a new one
        (a new word, or another way of saying it). An optional photo of the
        thing is checked by the image model as extra evidence.
        """
        meaning = normalise_meaning(meaning)
        if not meaning:
            raise ValueError("meaning is empty")
        if not speaker_id.strip() or not consent_id.strip():
            raise ValueError("every recording needs a speaker ID and a consent ID")

        audio = trim_silence(audio)
        vector = self.embedder.embed(audio)
        matches = [m for m in self._matches(vector) if m.confident]
        same = [m for m in matches if m.entry.meaning == meaning]

        if same:
            entry_id, new_entry = same[0].entry.id, False
            self.store.fill_spelling(entry_id, rohingyalish, hanifi)
        else:
            entry_id, new_entry = self.store.add_entry(meaning, rohingyalish, hanifi), True
        self.store.add_clip(
            entry_id, audio, speaker_id=speaker_id.strip(), consent_id=consent_id.strip(),
            embedding=vector, embedder=self.embedder_id, dialect_region=dialect_region,
            source=source,
        )

        vision = self.check_image(entry_id, image) if image is not None else None
        entries = self._entries()
        conflicts = [entries[m.entry.id] for m in matches if m.entry.meaning != meaning]
        return TeachResult(entries[entry_id], new_entry, conflicts, vision)

    def check_image(self, entry_id: int, image: np.ndarray) -> VisionCheck:
        """Ask the image model whether a photo shows the entry's meaning, and record the answer.

        It agrees only if the meaning beats every other known label (the
        vocabulary file plus all lexicon meanings) and clears a minimum score.
        """
        if self.labeler is None:
            raise RuntimeError("no image labeler loaded; open the lexicon with vision=True")
        meaning = self.store.entry(entry_id).meaning
        labels = self.labeler.label_image(image, [meaning, *self._known_labels(exclude=meaning)])
        own = next(label for label in labels if label.text == meaning)
        agrees = labels[0].text == meaning and own.score >= self.settings.vision_min_score
        self.store.add_vision_check(
            entry_id, score=own.score, top_label=labels[0].text, agrees=agrees,
            labeler=self.labeler_id,
        )
        return VisionCheck(own.score, labels[0].text, agrees)

    def suggest(self, image: np.ndarray, limit: int = 5) -> list[Label]:
        """Likely English meanings for a photo, to help a speaker say what it shows."""
        if self.labeler is None:
            raise RuntimeError("no image labeler loaded; open the lexicon with vision=True")
        return self.labeler.label_image(image, self._known_labels())[:limit]

    def reembed(self) -> int:
        """Recompute every clip's vector with the current audio embedder. Returns the count."""
        clips = self.store.clips()
        for clip in clips:
            vector = self.embedder.embed(load_wav(self.store.root / clip.path))
            self.store.set_embedding(clip.id, vector, self.embedder_id)
        return len(clips)

    # Reading

    def lookup(self, audio: Audio, limit: int = 5) -> list[Match]:
        """Entries that sound most like ``audio``, best first. Check ``confident`` before use."""
        return self._matches(self.embedder.embed(trim_silence(audio)))[:limit]

    def entries(self, status: Status | None = None) -> list[Entry]:
        return [e for e in self._entries().values() if status is None or e.status == status]

    def export_csv(self, path: str | Path, status: Status = Status.VERIFIED) -> int:
        """Write clips of entries with ``status`` in the ``data/clips.csv`` format, for training."""
        entries = {e.id: e for e in self.entries(status)}
        rows = [c for c in self.store.clips() if c.entry_id in entries]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["clip_id", "speaker_id", "path", "duration_s", "english",
                             "rohingyalish", "hanifi", "dialect_region", "consent_id", "status"])
            for c in rows:
                e = entries[c.entry_id]
                writer.writerow([
                    f"lex{c.id}", c.speaker_id, (self.store.root / c.path).as_posix(),
                    f"{c.duration_s:.2f}", e.meaning, e.rohingyalish, e.hanifi,
                    c.dialect_region, c.consent_id, e.status.value,
                ])
        return len(rows)

    # Internals

    def _matches(self, vector: np.ndarray) -> list[Match]:
        """Best similarity per entry, over clips made by the current embedder."""
        clips = [c for c in self.store.clips() if c.embedder == self.embedder_id]
        if not clips:
            return []
        sims = np.stack([c.embedding for c in clips]) @ vector
        best: dict[int, float] = {}
        for clip, sim in zip(clips, sims):
            best[clip.entry_id] = max(best.get(clip.entry_id, -1.0), float(sim))
        entries = self._entries()
        threshold = self.settings.match_threshold
        return sorted(
            (Match(entries[i], s, s >= threshold) for i, s in best.items()),
            key=lambda m: m.similarity,
            reverse=True,
        )

    def _entries(self) -> dict[int, Entry]:
        rows = self.store.entries()
        clips = self.store.clips()
        speakers: dict[int, set[str]] = defaultdict(set)
        for c in clips:
            speakers[c.entry_id].add(c.speaker_id)

        # Same-sounding clips filed under different meanings: each side disputes the other.
        meaning = {r.id: r.meaning for r in rows}
        conflicts: dict[int, set[str]] = defaultdict(set)
        comparable = [c for c in clips if c.embedder == self.embedder_id]
        if len(comparable) > 1:
            vectors = np.stack([c.embedding for c in comparable])
            close = np.argwhere(np.triu(vectors @ vectors.T, k=1) >= self.settings.match_threshold)
            for i, j in close:
                a, b = comparable[i], comparable[j]
                if meaning[a.entry_id] != meaning[b.entry_id]:
                    conflicts[a.entry_id].add(b.speaker_id)
                    conflicts[b.entry_id].add(a.speaker_id)

        return {r.id: self._entry(r, speakers[r.id], conflicts[r.id]) for r in rows}

    def _entry(self, row: EntryRow, speakers: set[str], conflicts: set[str]) -> Entry:
        # A speaker who gives both meanings is describing a word with two senses, not disagreeing.
        vision = self.store.vision_agrees(row.id)
        support = Support(len(speakers), vision, len(conflicts - speakers))
        status = decide(support, self.settings.min_speakers, self.settings.max_conflict_share)
        return Entry(row.id, row.meaning, row.rohingyalish, row.hanifi, status, support)

    def _known_labels(self, exclude: str = "") -> list[str]:
        labels = load_vocabulary(self.settings.vocabulary)
        labels += [r.meaning for r in self.store.entries()]
        return [x for x in dict.fromkeys(labels) if x != exclude]


def _backend_id(backend: str, instance: object) -> str:
    """Identifies which model made a vector or label, e.g. ``wav2vec2:facebook/...@layer12``."""
    return f"{backend}:{getattr(instance, 'name', '')}"
