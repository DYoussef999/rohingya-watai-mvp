# Rohingya Translate (working name)

Speech translation from **Rohingya** to **English**, running on the user's own device.

Rohingya is spoken by over a million people but has no widely used written form (Hanifi Rohingya and the Latin-based "Rohingyalish" exist but few speakers read them). So the main path goes straight from **speech to English** without needing a Rohingya transcript.

> Status: project skeleton. The pipeline runs end to end with a stub backend; Whisper is wired in but untrained on Rohingya.

## How it works

```
                    ┌──────────────── direct (default) ────────────────┐
 recording.wav ──►  │  SpeechTranslator  (e.g. fine-tuned Whisper)     │ ──► English text ──► [Synthesizer] ──► spoken English
                    └──────────────────────────────────────────────────┘
                    ┌──────────────── cascade ─────────────────────────┐
                    │  SpeechToText ──► Rohingya text ──► TextTranslator│
                    └──────────────────────────────────────────────────┘
```

Each box is a small interface in [`stages/base.py`](src/rohingya_translate/stages/base.py). Backends are chosen in a TOML config, so swapping a model never touches the pipeline.

## Setup (Windows)

Use Python 3.11 or 3.12; ML libraries are slow to support the newest Python.

```
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"            # core + tests
.venv\Scripts\python -m pip install -e ".[whisper]"        # add Whisper
.venv\Scripts\python -m pytest
```

## Usage

```
.venv\Scripts\rtranslate recording.wav                    # uses configs/default.toml
.venv\Scripts\rtranslate recording.wav --config my.toml --json
```

Input is 16-bit WAV. Convert phone recordings with `ffmpeg -i in.m4a -ar 16000 -ac 1 out.wav`.

## Layout

```
configs/            pipeline settings (TOML)
src/rohingya_translate/
  audio.py          load + normalise audio (mono, 16 kHz, float32)
  config.py         settings dataclasses
  pipeline.py       runs the configured stages
  registry.py       backend name -> class
  stages/           interfaces (base.py) and one module per backend
training/           fine-tuning and evaluation scripts (later)
data/               recordings and transcripts, gitignored
docs/               brief, roadmap, dependencies
tests/
```

## License

MIT. Dependencies and model weights must be MIT, BSD or Apache 2.0 (see [docs/dependencies.md](docs/dependencies.md)).
