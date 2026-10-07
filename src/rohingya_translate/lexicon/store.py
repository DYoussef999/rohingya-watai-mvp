"""SQLite storage for the lexicon: entries, their recordings, and camera checks.

Layout on disk (under ``data/``, so never committed)::

    <root>/lexicon.db
    <root>/clips/<uuid>.wav

Photos are never stored; only what the image model concluded about them.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from rohingya_translate.audio import Audio, save_wav

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    meaning TEXT NOT NULL,            -- English gloss, normalised
    rohingyalish TEXT NOT NULL DEFAULT '',
    hanifi TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clips (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    path TEXT NOT NULL,               -- relative to the lexicon root
    speaker_id TEXT NOT NULL,
    consent_id TEXT NOT NULL,
    dialect_region TEXT NOT NULL DEFAULT '',
    duration_s REAL NOT NULL,
    source TEXT NOT NULL,             -- "teach" or "prompt"
    embedding BLOB NOT NULL,
    embedder TEXT NOT NULL,           -- vectors from different embedders are not comparable
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vision_checks (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    score REAL NOT NULL,              -- image model's score for the entry's meaning
    top_label TEXT NOT NULL,
    agrees INTEGER NOT NULL,
    labeler TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def normalise_meaning(text: str) -> str:
    """Lower-case and collapse whitespace, so "Water " and "water" are one meaning."""
    return " ".join(text.lower().split())


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class EntryRow:
    id: int
    meaning: str
    rohingyalish: str
    hanifi: str
    created_at: str


@dataclass
class ClipRow:
    id: int
    entry_id: int
    path: str
    speaker_id: str
    consent_id: str
    dialect_region: str
    duration_s: float
    source: str
    embedding: np.ndarray
    embedder: str


class LexiconStore:
    """Plain reads and writes. Matching and trust rules live in ``Lexicon``."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        (self.root / "clips").mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "lexicon.db")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # Entries

    def add_entry(self, meaning: str, rohingyalish: str = "", hanifi: str = "") -> int:
        with self.db:
            cur = self.db.execute(
                "INSERT INTO entries (meaning, rohingyalish, hanifi, created_at) VALUES (?,?,?,?)",
                (normalise_meaning(meaning), rohingyalish.strip(), hanifi.strip(), _now()),
            )
        return cur.lastrowid

    def fill_spelling(self, entry_id: int, rohingyalish: str = "", hanifi: str = "") -> None:
        """Set spellings that are still empty; never overwrite an existing one."""
        with self.db:
            for column, value in (("rohingyalish", rohingyalish), ("hanifi", hanifi)):
                if value.strip():
                    self.db.execute(
                        f"UPDATE entries SET {column} = ? WHERE id = ? AND {column} = ''",
                        (value.strip(), entry_id),
                    )

    def entry(self, entry_id: int) -> EntryRow:
        row = self.db.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if row is None:
            raise KeyError(f"no lexicon entry {entry_id}")
        return EntryRow(**dict(row))

    def entries(self) -> list[EntryRow]:
        return [EntryRow(**dict(r)) for r in self.db.execute("SELECT * FROM entries ORDER BY id")]

    # Clips

    def add_clip(
        self,
        entry_id: int,
        audio: Audio,
        *,
        speaker_id: str,
        consent_id: str,
        embedding: np.ndarray,
        embedder: str,
        dialect_region: str = "",
        source: str = "teach",
    ) -> int:
        """Save the recording under ``clips/`` and record who said it."""
        rel = f"clips/{uuid.uuid4().hex}.wav"
        save_wav(audio, self.root / rel)
        with self.db:
            cur = self.db.execute(
                "INSERT INTO clips (entry_id, path, speaker_id, consent_id, dialect_region,"
                " duration_s, source, embedding, embedder, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (entry_id, rel, speaker_id, consent_id, dialect_region, audio.duration, source,
                 np.asarray(embedding, dtype=np.float32).tobytes(), embedder, _now()),
            )
        return cur.lastrowid

    def clips(self, entry_id: int | None = None) -> list[ClipRow]:
        query, args = "SELECT * FROM clips", ()
        if entry_id is not None:
            query, args = query + " WHERE entry_id = ?", (entry_id,)
        rows = self.db.execute(query + " ORDER BY id", args).fetchall()
        return [self._clip(r) for r in rows]

    def set_embedding(self, clip_id: int, embedding: np.ndarray, embedder: str) -> None:
        with self.db:
            self.db.execute(
                "UPDATE clips SET embedding = ?, embedder = ? WHERE id = ?",
                (np.asarray(embedding, dtype=np.float32).tobytes(), embedder, clip_id),
            )

    @staticmethod
    def _clip(row: sqlite3.Row) -> ClipRow:
        data = dict(row)
        data.pop("created_at")
        data["embedding"] = np.frombuffer(data["embedding"], dtype=np.float32)
        return ClipRow(**data)

    # Vision checks

    def add_vision_check(
        self, entry_id: int, *, score: float, top_label: str, agrees: bool, labeler: str
    ) -> None:
        with self.db:
            self.db.execute(
                "INSERT INTO vision_checks (entry_id, score, top_label, agrees, labeler,"
                " created_at) VALUES (?,?,?,?,?,?)",
                (entry_id, score, top_label, int(agrees), labeler, _now()),
            )

    def vision_agrees(self, entry_id: int) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM vision_checks WHERE entry_id = ? AND agrees = 1 LIMIT 1", (entry_id,)
        ).fetchone()
        return row is not None
