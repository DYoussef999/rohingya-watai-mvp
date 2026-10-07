"""A Rohingya dictionary that grows from recordings and checks itself with images."""

from rohingya_translate.lexicon.lexicon import (
    Entry,
    Lexicon,
    Match,
    TeachResult,
    VisionCheck,
    list_prompts,
    load_vocabulary,
    meaning_from_prompt,
)
from rohingya_translate.lexicon.policy import Status, Support, decide
from rohingya_translate.lexicon.store import LexiconStore, normalise_meaning

__all__ = [
    "Entry", "Lexicon", "LexiconStore", "Match", "Status", "Support", "TeachResult",
    "VisionCheck", "decide", "list_prompts", "load_vocabulary", "meaning_from_prompt",
    "normalise_meaning",
]
