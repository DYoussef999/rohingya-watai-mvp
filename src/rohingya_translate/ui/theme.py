"""Colours and fonts: a dark, calm theme. Each section has its own accent colour so it can be
recognised without reading.
"""

from __future__ import annotations

FONT = "Segoe UI"
FONT_STRONG = "Segoe UI Semibold"  # lighter than bold; reads as more refined on dark

BG = "#0E1014"  # near-black, slightly blue
SURFACE = "#161920"  # cards and panels
RAISED = "#1D212A"  # inputs, hover
INK = "#ECEEF2"
MUTED = "#8B92A0"
LINE = "#2A2F3A"
FAINT = "#222631"
ON_ACCENT = "#0B0D11"  # text and icons on a filled accent

SPEAK = "#2DD4BF"  # teal
WORDS = "#A78BFA"  # violet
TEACH = "#FBBF24"  # amber
SEE = "#60A5FA"  # blue
RECORD = "#FB7185"  # rose while recording
GOOD = "#34D399"
OK = "#60A5FA"
NEUTRAL = "#6B7280"
WARN = "#FB923C"

# Dictionary status -> (colour, icon, caption)
STATUS = {
    "verified": (GOOD, "check", "verified"),
    "corroborated": (OK, "check2", "likely"),
    "proposed": (NEUTRAL, "dot", "new"),
    "disputed": (WARN, "warning", "unclear"),
}


def font(size: int, weight: str = "normal") -> tuple[str, int, str]:
    if weight == "bold":
        return (FONT_STRONG, size, "normal")
    return (FONT, size, weight)


def _mix(colour: str, other: str, amount: float) -> str:
    a = [int(colour[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02x}" for x, y in zip(a, b))


def shade(colour: str, factor: float) -> str:
    """factor > 1: fade towards the background (2.0 = background), for tints and halos.
    factor < 1: brighten (hover on a filled button)."""
    if factor >= 1:
        return _mix(colour, SURFACE, min(1.0, factor - 1))
    return _mix(colour, "#FFFFFF", 1 - factor)
