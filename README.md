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

## Quick start

Double-click **`run.bat`**. The first time, it sets up the Python packages (needs internet once), then it opens the app.

To see every tab filled in, double-click **`demo.bat`** instead. It builds made-up demo data in `data/demo/` (about 45 words with coloured picture cards, 15 phrases, 6 demo speakers, and dictionary entries in every status, all with tone-pattern "recordings") and opens the app with `configs/demo.toml`. The data is rebuilt fresh on each launch and never touches the real dictionary. Nothing in it is real Rohingya.

## Setup (Windows)

New to Python? Follow the step-by-step [getting started guide](docs/getting-started.md).

Use Python 3.11 or 3.12; ML libraries are slow to support the newest Python.

```
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"            # core + tests
.venv\Scripts\python -m pip install -e ".[whisper]"        # add Whisper
.venv\Scripts\python -m pip install -e ".[lexicon]"        # add dictionary models (XLS-R, SigLIP, webcam)
.venv\Scripts\python -m pytest
```

## Usage

```
.venv\Scripts\rtranslate-gui                             # desktop app (same as run.bat)
.venv\Scripts\rtranslate recording.wav                    # uses configs/default.toml
.venv\Scripts\rtranslate recording.wav --config configs\models.toml --json
```

`configs/default.toml` uses stub backends (instant, no downloads). `configs/models.toml` switches on the real models; install `.[whisper,lexicon]` first. In the app, choose the settings file with the gear button (top right).

### Self-growing dictionary

Speakers teach words by recording them. Recordings of the same word are matched by sound, and an image model checks photos against the claimed meaning. An entry becomes **verified** once enough different speakers agree (default 3; an agreeing camera check can stand in for one of them). Details are in [docs/brief.md](docs/brief.md).

```
rlexicon teach water_S014.wav --meaning water --speaker S014 --consent C-0091 [--photo cup.jpg | --camera]
rlexicon teach clip.wav --prompt data\prompts\cooking_pot.jpg --speaker S014 --consent C-0091
rlexicon lookup unknown.wav                  # which word is this?
rlexicon see --camera                        # suggest English words for what the webcam sees
rlexicon check 12 --photo pot.jpg            # camera check for entry 12
rlexicon list --status verified
rlexicon export data\lexicon_verified.csv    # training data for fine-tuning
```

Input is 16-bit WAV. Convert phone recordings with `ffmpeg -i in.m4a -ar 16000 -ac 1 out.wav`.

## Layout

```
configs/            pipeline settings (TOML) and the image-check vocabulary
run.bat, demo.bat   one-click launchers (demo.bat: made-up data in every tab)
src/rohingya_translate/
  app.py            desktop app shell; ui/ holds its screens, icons and widgets
  recorder.py       microphone recording and playback
  audio.py          load + normalise audio (mono, 16 kHz, float32)
  images.py         image files and webcam
  lexicon/          self-growing dictionary: storage, matching, agreement rules
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
