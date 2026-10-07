# Dependencies and licenses

Only MIT, BSD or Apache 2.0. Check the license **before** adding anything, including model weights and datasets, which often have their own licenses.

| Package / asset | Used for | License | Extra |
|---|---|---|---|
| numpy | audio arrays | BSD-3 | core |
| faster-whisper | Whisper inference (CTranslate2) | MIT | `whisper` |
| CTranslate2 | inference engine under faster-whisper | MIT | `whisper` |
| Whisper weights (OpenAI) | speech model | MIT | `whisper` |
| torch | fine-tuning | BSD-3 | `train` |
| transformers, datasets, peft | fine-tuning | Apache 2.0 | `train` |
| opencv-python-headless | vision (later) | Apache 2.0 | `vision` |
| pytest | tests | MIT | `dev` |
| ruff | linting | MIT | `dev` |

To check before use: any Rohingya dataset (many academic datasets are non-commercial or research-only, which is not allowed here); any TTS voice.
