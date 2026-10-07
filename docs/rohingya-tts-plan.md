# Plan: a trained Rohingya voice

Status: **plan only** (roadmap step 7). Decided 2026-10-07: no synthetic Rohingya voice until one can be trained from real, consented recordings. Until then, Rohingya audio in the app is only ever **real recordings** from the dictionary, and English is read aloud with Windows' built-in voices.

## Why not now

- **No usable voice exists.** No Rohingya text-to-speech model exists under a permissive licence. Meta's MMS-TTS covers about 1,100 languages but not Rohingya, and its weights are CC-BY-NC, which this project's licence rules exclude.
- **Faking it would mislead.** Reading Rohingyalish spellings with an English or Bengali voice would mispronounce words. Native speakers would hear the errors at once, and in health or legal conversations a wrong word is worse than silence.
- **The usual pronunciation engine is GPL.** eSpeak NG, which many open TTS systems use to turn text into sounds, is GPL-3.0. A Rohingya voice therefore has to learn straight from letters to sounds (see below), which is feasible because Rohingyalish is spelled close to how it sounds.

## What a voice needs

A TTS model learns from **pairs: a recording plus the exact text of what was said.** So this depends on two things the project doesn't have yet.

1. **A spelling convention.** The model reads text, so every training recording needs a transcript in one consistent spelling. This is the open decision in [brief.md](brief.md): Rohingyalish (Latin letters, easier to type and to train on) or Hanifi Rohingya. Mixed or inconsistent spellings will produce a voice that mispronounces.
2. **Enough clean, consented speech.** These are typical figures for current models, to be confirmed by experiment:

   | Goal | Speech needed | Notes |
   |---|---|---|
   | First test voice | 1–2 hours, one speaker | Fine-tuned from a pretrained model; robotic but understandable |
   | Usable single voice | 5–10 hours, one speaker | Comparable to early open voices in other low-resource languages |
   | A male and a female voice, dialect coverage | 10+ hours over several speakers | Multi-speaker model |

   This is **read speech**: a speaker reads prepared sentences in a quiet room, one sentence per clip of 2–10 seconds. Single-word dictionary clips help, but they aren't enough on their own: a voice trained only on isolated words can't produce natural sentences.

## Consent: stronger than for the dictionary

A trained voice can say **anything** in that person's voice, so the consent for this is different from consent to have a word in the dictionary.

- **Separate, explicit consent** to having a synthetic voice built from the recordings, recorded as its own field (not covered by the existing `consent_id`).
- **The speaker decides how the voice may be used.** For example, in this app only, never for impersonation, and never released as a cloneable model.
- **Withdrawal:** if a voice speaker withdraws, the voice is retired and retrained without them. Model files are versioned with the list of speakers they contain.
- **Labelled as a computer voice.** The app must always show synthetic speech as a computer voice, visually distinct from real recordings (see below).
- **Fair pay** for voice speakers: reading for hours is real work.

## Data collection, using what the app already has

1. **A "Read" mode in the Teach tab.** It shows one sentence at a time (written for the helper, with a picture where possible). The speaker says it, and the recording is saved with its transcript. This reuses the press-to-talk microphone and the waveform check.
2. **A sentence list (corpus)** written with native speakers. It should cover all the sounds of Rohingya, plus high-value phrases (health, directions, family, documents), the phrasebook, and numbers and dates.
3. **Quality checks before training:** clipping, background noise, and the transcript matching the audio (a second speaker listens and confirms, like the dictionary's agreement rule).
4. **Storage:** `data/tts/<speaker>/<clip>.wav` plus `metadata.csv` (path, text, speaker, voice-consent ID). Never committed, like all of `data/`.

## Model options (licences checked 2026-10-07)

All must be MIT, BSD or Apache 2.0, **including the pretrained weights** used as a starting point.

| Option | Code licence | Fit |
|---|---|---|
| **VITS** (jaywalnut310/vits) | MIT | Proven end to end; can train on characters directly (no eSpeak); exports to ONNX for phones |
| **Matcha-TTS** | MIT | Fast, small, good quality from little data; character input possible |
| **ESPnet** (VITS and other recipes) | Apache 2.0 | Research toolkit with full training recipes; heavier |
| **StyleTTS 2** | MIT | High quality, needs more data and compute; check the licence of any pretrained weights |
| Piper (rhasspy/piper) | MIT, archived | Good for phones, but its successor piper1 is GPL-3.0 and it depends on eSpeak (GPL). Excluded unless used in character mode with the old MIT code |
| Coqui TTS / XTTS | MPL-2.0 / non-commercial weights | Excluded |
| MMS-TTS | CC-BY-NC weights | Excluded |
| F5-TTS | MIT code, non-commercial pretrained weights | Excluded unless trained from scratch |

**Suggested path:** VITS or Matcha-TTS with **character input on Rohingyalish**. Start from scratch or from a permissively licensed English checkpoint (character models transfer poorly across scripts, so scratch training with 5+ hours is the safer baseline). Train on a single GPU, then export to ONNX.

## How it plugs into the app

- **A new backend:** a `Synthesizer` implementation (for example `rohingya_vits`) registered in `registry.py` and selected under a new `[rohingya_voice]` config section. The existing English voice stays under `[synthesizer]`.
- **Text in, audio out:** for a dictionary word, the Rohingyalish spelling. For a sentence, its Rohingyalish text, which will need an English → Rohingya text translator (a later step, with its own data needs).
- **Real recordings come first.** If a word has a real recording, play that. Only use the computer voice when there is none.
- **A clear visual difference:** real recordings keep the person icon, while the computer voice gets a distinct "computer voice" badge and colour. This follows the brief's honest-output principle.

## How to know it works

Native speakers judge it; numbers alone aren't enough.

- **Understandability:** a listener hears a synthetic word or sentence and picks the matching picture, or repeats it back. The target is at least 90% correct on the test set before release.
- **Naturalness:** native listeners rate clips from 1 to 5, mixed in with real recordings they can't tell apart by label.
- **Dialect check:** listeners from different regions (see dialect tagging in the brief) all find it understandable.
- **Safety review:** speakers who gave their voice approve how it sounds before it ships.

## Milestones

1. Decide the spelling convention (Rohingyalish or Hanifi). **Blocks everything else.**
2. Write the voice-consent form and add a `voice_consent_id` to the data format.
3. Write the sentence corpus with native speakers (about 2,000 sentences to start).
4. Add a "Read" mode to the Teach tab, then record 1–2 hours from one consenting speaker.
5. Train a test voice (VITS or Matcha, character input) and run the understandability test.
6. Collect 5–10 hours, retrain, and add a second voice.
7. Add the `rohingya_vits` backend and the computer-voice badge, behind a setting that is off by default.
8. Run the listening tests with speakers, then decide whether to switch it on.
