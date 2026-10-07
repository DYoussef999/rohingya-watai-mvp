"""When does the lexicon trust an entry? Agreement between independent sources."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    """How far an entry's meaning is supported. Only VERIFIED should be shown as fact."""

    PROPOSED = "proposed"  # one source
    CORROBORATED = "corroborated"  # two sources agree
    VERIFIED = "verified"  # enough independent agreement
    DISPUTED = "disputed"  # speakers disagree about what this word means


@dataclass(frozen=True)
class Support:
    """The evidence behind one entry."""

    speakers: int  # distinct speakers who recorded this word with this meaning
    vision: bool  # a camera check agreed with the meaning
    conflicts: int  # distinct other speakers who said the same-sounding word means something else


def decide(support: Support, min_speakers: int = 3, max_conflict_share: float = 0.25) -> Status:
    """Status from evidence. A camera check can replace one speaker, but never verifies alone."""
    total = support.speakers + support.conflicts
    if total and support.conflicts / total > max_conflict_share:
        return Status.DISPUTED
    if support.speakers >= min_speakers or (
        support.vision and support.speakers >= max(1, min_speakers - 1)
    ):
        return Status.VERIFIED
    if support.speakers + support.vision >= 2:
        return Status.CORROBORATED
    return Status.PROPOSED
