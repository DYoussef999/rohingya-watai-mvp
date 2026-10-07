# Dependencies and licenses

Only MIT, BSD or Apache 2.0. Check the license **before** adding anything, including model weights and datasets, which often have their own licenses.

| Package / asset | Used for | License | Extra |
|---|---|---|---|
| numpy | audio arrays | BSD-3 | core |
| sounddevice (+ bundled PortAudio, cffi) | microphone recording and playback | MIT (PortAudio: MIT-style, cffi: MIT-0) | core |
| faster-whisper | Whisper inference (CTranslate2) | MIT | `whisper` |
| CTranslate2 | inference engine under faster-whisper | MIT | `whisper` |
| Whisper weights (OpenAI) | speech model | MIT | `whisper` |
| torch | fine-tuning | BSD-3 | `train` |
| transformers, datasets, peft | fine-tuning | Apache 2.0 | `train` |
| torch, transformers | lexicon: audio embeddings, image labels | BSD-3, Apache 2.0 | `lexicon` |
| sentencepiece, protobuf | SigLIP tokenizer | Apache 2.0, BSD-3 | `lexicon` |
| opencv-python-headless | image files, webcam, resizing | Apache 2.0 | `lexicon`, `vision` |
| XLS-R 300M weights (`facebook/wav2vec2-xls-r-300m`, Meta) | spoken-word embeddings | Apache 2.0 | `lexicon` |
| SigLIP base weights (`google/siglip-base-patch16-224`, Google) | image labelling | Apache 2.0 | `lexicon` |
| pytest | tests | MIT | `dev` |
| ruff | linting | MIT | `dev` |

Uses the operating system, no package: Windows System.Speech voices (David, Zira) for reading English aloud.

Rejected for a Rohingya voice (see rohingya-tts-plan.md): Coqui TTS (MPL-2.0), MMS-TTS weights (CC-BY-NC), piper1 and eSpeak NG (GPL-3.0).

Rejected: OpenAI CLIP weights on Hugging Face (no license stated on the model card).

To check before use: any Rohingya dataset (many academic datasets are non-commercial or research-only, which is not allowed here); any TTS voice.
