"""Image labelling with SigLIP (Apache 2.0) via transformers.

Install with ``pip install -e ".[lexicon]"``. SigLIP scores each label on its own
(a sigmoid, not a softmax), so a score says how well that label fits the photo
regardless of the other candidates.
"""

from __future__ import annotations

import numpy as np

from rohingya_translate.config import StageConfig
from rohingya_translate.stages.base import Label
from rohingya_translate.stages.torch_device import pick_device

DEFAULT_MODEL = "google/siglip-base-patch16-224"


class SiglipBackend:
    """Implements ImageLabeler."""

    def __init__(self, config: StageConfig) -> None:
        try:
            import cv2  # noqa: F401  (needed for resizing)
            from transformers import AutoModel, AutoTokenizer
        except ImportError as e:
            raise ImportError('SigLIP backend needs: pip install -e ".[lexicon]"') from e

        name = config.model or DEFAULT_MODEL
        self.name = name
        self.device = pick_device(config.device)
        self.model = AutoModel.from_pretrained(name).to(self.device).eval()
        self.tokenizer = AutoTokenizer.from_pretrained(name)
        self.image_size = self.model.config.vision_config.image_size
        self.max_length = self.model.config.text_config.max_position_embeddings
        self.prompt = config.options.get("prompt", "a photo of {}.")
        self._text_cache: dict = {}  # label -> embedding

    def label_image(self, image: np.ndarray, candidates: list[str]) -> list[Label]:
        import torch

        if not candidates:
            return []
        # Same maths as SiglipModel.forward, but label embeddings are cached:
        # encoding the label list is most of the work, and it rarely changes.
        with torch.no_grad():
            pixels = self._preprocess(image)
            image_embed = self.model.vision_model(pixel_values=pixels).pooler_output
            image_embed = image_embed / image_embed.norm(dim=-1, keepdim=True)
            logits = self._text_embeds(candidates) @ image_embed[0]
            logits = logits * self.model.logit_scale.exp() + self.model.logit_bias
        scores = torch.sigmoid(logits).tolist()
        return sorted(
            (Label(c, float(s)) for c, s in zip(candidates, scores)),
            key=lambda label: label.score,
            reverse=True,
        )

    def _text_embeds(self, labels: list[str]):
        """Unit-length embeddings for ``labels``, encoding only ones not seen before."""
        import torch

        missing = [label for label in dict.fromkeys(labels) if label not in self._text_cache]
        if missing:
            # SigLIP was trained with max-length padding; other padding hurts accuracy.
            tokens = self.tokenizer(
                [self.prompt.format(label) for label in missing], padding="max_length",
                max_length=self.max_length, truncation=True, return_tensors="pt",
            )
            with torch.no_grad():
                input_ids = tokens["input_ids"].to(self.device)
                embeds = self.model.text_model(input_ids=input_ids).pooler_output
            embeds = embeds / embeds.norm(dim=-1, keepdim=True)
            self._text_cache.update(zip(missing, embeds))
        return torch.stack([self._text_cache[label] for label in labels])

    def _preprocess(self, image: np.ndarray):
        """RGB uint8 -> resized, scaled to [-1, 1], as a 1 x 3 x H x W tensor."""
        import cv2
        import torch

        resized = cv2.resize(image, (self.image_size, self.image_size),
                             interpolation=cv2.INTER_CUBIC)
        pixels = resized.astype(np.float32) / 127.5 - 1.0
        return torch.from_numpy(pixels.transpose(2, 0, 1)).unsqueeze(0).to(self.device)
