# training/

Fine-tuning and evaluation scripts go here (roadmap steps 4–5 in `docs/brief.md`). Install with `pip install -e ".[train]"`.

Planned:
- `evaluate.py`: run a config over `data/splits/test.txt`, report chrF/BLEU (English) and WER/CER (transcripts).
- `finetune_whisper.py`: LoRA fine-tune of Whisper `small`/`medium` on Rohingya speech → English text; writes to `models/<run_name>/`, convert to CTranslate2 for the `whisper` backend.

Output models go to `models/` (gitignored).
