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
1. **Skeleton** (done): config, audio loading, pipeline with direct/cascade modes, stub + Whisper backends, tests.
2. **Baseline:** run stock Whisper (`translate` task, Bengali hint) on a few Rohingya clips and record how bad it is. This is the number to beat.
3. **Data:** collect consented recordings with English translations (and Rohingyalish transcripts where possible). Define a fixed test set kept out of training.
4. **Evaluation:** `training/evaluate.py` with BLEU/chrF for translation and WER/CER for transcription.
5. **Fine-tune Whisper** (LoRA on `small`/`medium`) for speech → English; compare against the baseline.
6. **Usable app:** live microphone input with voice activity detection, streaming results.
7. **Two-way:** English → Rohingya *speech* (needs a Rohingya TTS voice; hardest part).
8. **Mobile/offline:** export to CTranslate2/ONNX, quantise, run on a phone.

## Feature ideas (later)
- **Phrasebook mode:** a curated list of high-value phrases (medical, legal, directions) with verified translations and recorded audio, which works even when the model is uncertain.
- **Speaker-friendly data collection tool:** prompt a speaker with an English sentence or an image, record their Rohingya, save with consent metadata.
- **Computer vision:** read Hanifi Rohingya or Rohingyalish text from photos (`ImageTextReader` interface); image prompts for data collection; possibly lip-reading to help in noisy camps (research-level).
- **Conversation view:** two-sided, turn-taking UI for face-to-face use.
- **Community corrections:** users fix translations locally, exported (with consent) as new training data.
- **Dialect tagging:** record the speaker's region so models can be checked for dialect bias.

## Open decisions
- Final app platform: desktop Python first; then mobile (Flutter / React Native / native) or browser (WebGPU + ONNX)?
- Transcription convention for the cascade path: Rohingyalish or Hanifi?
- Where training data comes from, and who partners on it (community organisations, existing research datasets).
