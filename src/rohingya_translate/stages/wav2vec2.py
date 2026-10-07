"""Spoken-word embeddings from wav2vec 2.0 / XLS-R (Apache 2.0) via transformers.

Install with ``pip install -e ".[lexicon]"``. The default, XLS-R 300M, was
pretrained on 128 languages without labels, so it captures speech sounds in
languages it was never taught, Rohingya included. A middle layer is mean-pooled
into one vector per clip, which works for single words; comparing longer
phrases would need frame-level alignment (e.g. DTW) instead.
"""

from __future__ import annotations

import numpy as np

from rohingya_translate.audio import Audio
from rohingya_translate.config import StageConfig
from rohingya_translate.stages.torch_device import pick_device

DEFAULT_MODEL = "facebook/wav2vec2-xls-r-300m"
MIN_SAMPLES = 1_600  # 0.1 s; the model's convolutions need some audio to work with


class Wav2Vec2Embedder:
    """Implements AudioEmbedder."""

    def __init__(self, config: StageConfig) -> None:
        try:
            from transformers import AutoModel
        except ImportError as e:
            raise ImportError('wav2vec2 backend needs: pip install -e ".[lexicon]"') from e

        self.device = pick_device(config.device)
        self.model = AutoModel.from_pretrained(config.model or DEFAULT_MODEL)
        self.model.to(self.device).eval()
        # Middle layers carry the most phonetic information in XLS-R.
        self.layer = int(config.options.get("layer", self.model.config.num_hidden_layers // 2))
        self.name = f"{config.model or DEFAULT_MODEL}@layer{self.layer}"

    def embed(self, audio: Audio) -> np.ndarray:
        import torch

        if len(audio.samples) < MIN_SAMPLES:
            raise ValueError("clip is too short to embed (under 0.1 s of sound)")
        x = audio.samples
        x = (x - x.mean()) / (x.std() + 1e-7)  # the normalisation XLS-R was trained with
        with torch.no_grad():
            out = self.model(
                torch.from_numpy(x).unsqueeze(0).to(self.device), output_hidden_states=True
            )
        vector = out.hidden_states[self.layer][0].mean(dim=0).cpu().numpy().astype(np.float32)
        return vector / (np.linalg.norm(vector) + 1e-12)
