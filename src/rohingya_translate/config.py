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
class Config:
    """Settings for the whole pipeline."""

    mode: str = "direct"  # "direct" or "cascade"
    synthesizer: str = ""  # backend name, "" for none
    speech_translator: StageConfig = field(default_factory=StageConfig)
    speech_to_text: StageConfig = field(default_factory=StageConfig)
    text_translator: StageConfig = field(default_factory=StageConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        pipeline = data.get("pipeline", {})
        config = cls(
            mode=pipeline.get("mode", "direct"),
            synthesizer=pipeline.get("synthesizer", ""),
            speech_translator=StageConfig.from_dict(data.get("speech_translator", {})),
            speech_to_text=StageConfig.from_dict(data.get("speech_to_text", {})),
            text_translator=StageConfig.from_dict(data.get("text_translator", {})),
        )
        if config.mode not in ("direct", "cascade"):
            raise ValueError(f"pipeline.mode must be 'direct' or 'cascade', not {config.mode!r}")
        return config


def load_config(path: str | Path | None = None) -> Config:
    """Load settings from ``path``, or the default config file."""
    with open(path or DEFAULT_CONFIG, "rb") as f:
        return Config.from_dict(tomllib.load(f))
