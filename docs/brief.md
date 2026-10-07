# Project brief

## Goal
Let a Rohingya speaker and an English speaker understand each other: speak Rohingya into a device and get English text (and later, English speech) back.

## Who it is for
Rohingya refugees and diaspora (Bangladesh, Malaysia, North America, …) and the caseworkers, doctors, teachers and volunteers working with them. Interpreters are scarce, and existing translation apps do not support Rohingya.

## Key facts that shape the design
- **Mostly spoken.** Scripts exist (Hanifi Rohingya, in Unicode since 2018; Rohingyalish, Latin-based) but most speakers don't read them. → Default to **direct speech-to-English**; a transcript is optional.
- **Low-resource.** Very little labelled audio exists. No mainstream ASR model supports it. → Whisper must be **fine-tuned**, and data collection is a first-class part of the project.
- **Related languages.** Rohingya is closely related to **Chittagonian** and more distantly to **Bengali**. Bengali is supported by Whisper and is a sensible starting point for transfer learning.
- **Sensitive users.** Speakers may be refugees discussing health, legal or asylum matters. → **On-device, no uploads, no telemetry** by default.

## Principles
1. **Local and private.** Inference runs on the device. Nothing is sent to a server unless the user explicitly opts in.
2. **Permissive licenses only** (MIT, BSD, Apache 2.0), including model weights and datasets.
3. **Consent for data.** Every recording used for training has documented informed consent. See `data/README.md`.
4. **Honest output.** Show confidence; never present a low-confidence guess as a fact. In medical or legal settings, the app supports a human interpreter; it does not replace one.
5. **Pluggable stages.** Every model sits behind an interface in `stages/base.py`.

## Roadmap
1. **Skeleton** (done): config, audio loading, pipeline with direct/cascade modes, stub + Whisper backends, tests. Desktop app (Tkinter, `run.bat` launcher) and self-growing lexicon added.
2. **Baseline:** run stock Whisper (`translate` task, Bengali hint) on a few Rohingya clips and record how bad it is. This is the number to beat.
3. **Data:** collect consented recordings with English translations (and Rohingyalish transcripts where possible). Define a fixed test set kept out of training.
4. **Evaluation:** `training/evaluate.py` with BLEU/chrF for translation and WER/CER for transcription.
5. **Fine-tune Whisper** (LoRA on `small`/`medium`) for speech → English; compare against the baseline.
6. **Usable app:** live microphone input with voice activity detection, streaming results.
7. **Two-way:** English → Rohingya *speech* (needs a Rohingya TTS voice; hardest part). Plan in [rohingya-tts-plan.md](rohingya-tts-plan.md); until then Rohingya audio is real recordings only. English is read aloud with built-in Windows voices (`windows` synthesizer).
8. **Mobile/offline:** export to CTranslate2/ONNX, quantise, run on a phone.

## Self-growing lexicon (built, needs real-data calibration)
A dictionary of spoken Rohingya words that grows in the app and checks itself. Code: `src/rohingya_translate/lexicon/`, CLI `rlexicon`, "Teach a word" and "Dictionary" tabs in the desktop app.

- **Keyed by sound, not spelling.** An entry is a meaning plus recordings of the word; Rohingyalish/Hanifi spellings are optional extras. Recordings are matched with an `AudioEmbedder` (default XLS-R 300M, mean-pooled middle layer; good for single words).
- **Every recording is one speaker vouching for a meaning.** Same-sounding recordings with the same meaning join one entry; a same-sounding recording with a different meaning marks both entries as conflicting (unless it is the same speaker, which means a word with two senses).
- **Computer vision corroborates.** An `ImageLabeler` (default SigLIP) checks whether a photo shows the claimed meaning, compared against `configs/vision_vocabulary.txt` and every lexicon meaning. Curated prompt pictures (`data/prompts/<meaning>.jpg`) give the meaning by file name. Photos are never stored, only the model's verdict.
- **Decision (2026-10-07): verification is automatic, by agreement.** `proposed` → `corroborated` (2 sources) → `verified` (`min_speakers` distinct speakers, default 3; one agreeing camera check can stand in for one speaker, never more). More than `max_conflict_share` disagreement → `disputed`. The owner chose this over trusted human reviewers for speed. Risk: a small group can verify a wrong meaning, so the UI always shows status, and medical/legal use still needs an interpreter.
- **Statuses are derived, never stored**, so changing thresholds or the embedder re-evaluates everything. `rlexicon reembed` recomputes vectors after switching models.
- **No live training.** Verified entries are exported (`rlexicon export`) in the `data/clips.csv` format and feed the next fine-tuning run (roadmap step 5).
- **Demo mode** (`demo.bat`, `src/rohingya_translate/demo.py`): synthetic data in `data/demo/` with a stand-in `demo` backend that only recognises its own tone-pattern recordings and colour cards. No Rohingya words are invented, so spelling columns stay empty.
- **Still to do:** calibrate `match_threshold` on real recordings; mining word candidates from full translated sentences (Whisper's translate-task timestamps don't line up with Rohingya words, so this waits for a fine-tuned model or the cascade path); microphone recording in the app.

## Interface principles (decided 2026-10-07)
Many users don't read English (and most don't read Rohingya scripts), so the app is visual first: one colour and one big drawn icon per section (Speak, Words, Teach, See); press-to-talk microphone recording (sounddevice) rather than file pickers; play buttons on every word; trust shown as colour, badges and people icons filling towards "verified"; teaching as three picture steps. English captions are short and aimed at helpers. Next steps: recorded Rohingya audio prompts for instructions, and testing with speakers.

## Feature ideas (later)
- **Phrasebook mode:** a curated list of high-value phrases (medical, legal, directions) with verified translations and recorded audio, which works even when the model is uncertain.
- **Speaker-friendly data collection tool:** prompt a speaker with an English sentence or an image, record their Rohingya, save with consent metadata.
- **Computer vision:** read Hanifi Rohingya or Rohingyalish text from photos (`ImageTextReader` interface); image prompts for data collection; possibly lip-reading to help in noisy camps (research-level).
- **Conversation view:** two-sided, turn-taking UI for face-to-face use.
- **Community corrections:** users fix translations locally, exported (with consent) as new training data.
- **Dialect tagging:** record the speaker's region so models can be checked for dialect bias.

## Open decisions
- Final app platform: desktop Python first (visual-first Tkinter app in `app.py` + `ui/`; decided 2026-10-07 over a local browser UI); then mobile (Flutter / React Native / native) or browser (WebGPU + ONNX)?
- Transcription convention for the cascade path: Rohingyalish or Hanifi?
- Where training data comes from, and who partners on it (community organisations, existing research datasets).
