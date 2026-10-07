"""Command line: ``rtranslate recording.wav [--config my.toml] [--json]``."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from rohingya_translate.audio import load_wav
from rohingya_translate.config import load_config
from rohingya_translate.pipeline import Pipeline


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Translate Rohingya speech to English.")
    parser.add_argument("audio", help="16-bit PCM WAV file")
    parser.add_argument("--config", help="TOML settings file (default: configs/default.toml)")
    parser.add_argument("--json", action="store_true", help="print full result as JSON")
    args = parser.parse_args(argv)

    pipeline = Pipeline(load_config(args.config))
    result = pipeline.run(load_wav(args.audio))

    if args.json:
        print(json.dumps({
            "english": asdict(result.english),
            "transcript": asdict(result.transcript) if result.transcript else None,
        }, ensure_ascii=False, indent=2))
        return
    if result.transcript:
        print(f"Rohingya: {result.transcript.text}")
    print(f"English:  {result.english.text}")


if __name__ == "__main__":
    main()
