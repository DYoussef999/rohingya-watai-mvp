# CLAUDE.md

Context for Claude Code in this repo. Read `docs/brief.md` before starting a roadmap step, and update it when a decision changes.

## What this is
A speech translator from Rohingya (a mostly spoken, low-resource language) to English. The default path is **direct speech → English** (no Rohingya transcript needed); a cascade path (speech → Rohingya text → English) exists for when a transcription convention is chosen.

## Rules
1. **Local and private.** Inference runs on-device. No uploads, telemetry or accounts unless the owner explicitly decides otherwise.
2. **Permissive licenses only** (MIT, BSD, Apache 2.0), including model weights and datasets. Check before adding; record in `docs/dependencies.md`.
3. **Never commit audio or personal data.** `data/` and `models/` are gitignored.
4. **Pluggable stages.** Models sit behind the protocols in `src/rohingya_translate/stages/base.py`, registered in `registry.py`, selected in `configs/*.toml`. Heavy ML imports are lazy so the core installs without them.
5. Ask before adding dependencies or making tradeoffs (quality vs. speed vs. model size).

## Commands
```
py -3.11 -m venv .venv && .venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\rtranslate path\to\clip.wav [--config configs\default.toml] [--json]
```

## Conventions
- Type hints and short docstrings on public functions; readable over clever.
- Tests for non-model logic (config, audio, pipeline wiring). Use the `echo` backend in tests; never download models in tests.
- Small, focused commits. Don't push without being asked.
