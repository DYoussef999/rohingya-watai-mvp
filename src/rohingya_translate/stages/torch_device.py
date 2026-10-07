"""Shared helper for backends built on PyTorch."""

from __future__ import annotations

from typing import Any


def pick_device(name: str) -> Any:
    """Turn a config device ("auto", "cpu", "cuda") into a torch device."""
    import torch

    if name == "auto":
        name = "cuda" if torch.cuda.is_available() else "cpu"
    return torch.device(name)
