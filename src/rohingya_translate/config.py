"""Pipeline settings, loaded from a TOML file (see ``configs/default.toml``)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "default.toml"


@dataclass
class StageConfig:
    """Which backend runs a stage, plus backend-specific options."""

    backend: str = "echo"
    model: str = ""
    device: str = "auto"
    source_language: str = ""
    options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StageConfig:
        """Known keys become fields; anything else goes into ``options``."""
        known = {f.name for f in fields(cls)} - {"options"}
        return cls(
            **{k: v for k, v in data.items() if k in known},
            options={k: v for k, v in data.items() if k not in known},
        )


@dataclass
class LexiconConfig:
    """Where the self-growing dictionary lives and when entries count as agreed."""

    path: str = "data/lexicon"
    # Cosine similarity above which two clips count as the same spoken word.
    # Depends on the audio embedder; calibrate on real recordings.
    match_threshold: float = 0.9
    # Distinct speakers who must agree on a meaning before it is "verified".
    # A matching camera check can stand in for one of them, never more.
    min_speakers: int = 3
    # An entry is "disputed" when more than this share of speakers gave another meaning.
    max_conflict_share: float = 0.25
    # Camera check passes if the meaning is the top label and scores at least this.
    # SigLIP scores each label on its own and conservatively; right answers often score 0.02-0.3.
    vision_min_score: float = 0.01
    # Pictures shown to speakers, named after what they show (e.g. cooking_pot.jpg).
    prompts: str = "data/prompts"
    # Extra labels to compare against in camera checks (one per line).
    vocabulary: str = "configs/vision_vocabulary.txt"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LexiconConfig:
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown [lexicon] settings: {sorted(unknown)}")
        return cls(**data)


@dataclass
class Config:
    """Settings for the whole pipeline."""

    mode: str = "direct"  # "direct" or "cascade"
    synthesizer: str = ""  # backend name, "" for none
    read_aloud: bool = True  # the app reads English results aloud when a synthesizer is set
    voice: StageConfig = field(default_factory=StageConfig)  # [synthesizer] options
    speech_translator: StageConfig = field(default_factory=StageConfig)
    speech_to_text: StageConfig = field(default_factory=StageConfig)
    text_translator: StageConfig = field(default_factory=StageConfig)
    audio_embedder: StageConfig = field(default_factory=StageConfig)
    image_labeler: StageConfig = field(default_factory=StageConfig)
    lexicon: LexiconConfig = field(default_factory=LexiconConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        pipeline = data.get("pipeline", {})
        config = cls(
            mode=pipeline.get("mode", "direct"),
            synthesizer=pipeline.get("synthesizer", ""),
            read_aloud=pipeline.get("read_aloud", True),
            voice=StageConfig.from_dict(
                {**data.get("synthesizer", {}), "backend": pipeline.get("synthesizer", "")}),
            speech_translator=StageConfig.from_dict(data.get("speech_translator", {})),
            speech_to_text=StageConfig.from_dict(data.get("speech_to_text", {})),
            text_translator=StageConfig.from_dict(data.get("text_translator", {})),
            audio_embedder=StageConfig.from_dict(data.get("audio_embedder", {})),
            image_labeler=StageConfig.from_dict(data.get("image_labeler", {})),
            lexicon=LexiconConfig.from_dict(data.get("lexicon", {})),
        )
        if config.mode not in ("direct", "cascade"):
            raise ValueError(f"pipeline.mode must be 'direct' or 'cascade', not {config.mode!r}")
        return config


def load_config(path: str | Path | None = None) -> Config:
    """Load settings from ``path``, or the default config file."""
    with open(path or DEFAULT_CONFIG, "rb") as f:
        return Config.from_dict(tomllib.load(f))
