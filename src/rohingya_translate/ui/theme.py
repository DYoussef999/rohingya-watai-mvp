"""Colours and fonts: a simple, friendly dark theme (in the spirit of Duolingo's dark mode).

Each section has one colour so it can be recognised without reading.
"""

from __future__ import annotations

FONT = "Segoe UI"
FONT_STRONG = "Segoe UI Semibold"
FONT_HEAVY = "Segoe UI Black"  # big friendly headings and button labels

BG = "#131F24"  # deep slate
SURFACE = "#131F24"  # cards sit on the background, separated by borders
RAISED = "#202F36"  # inputs, hover, selected
INK = "#F1F7FB"
MUTED = "#8A9BA3"
LINE = "#37464F"  # borders and button lips
FAINT = "#202F36"
ON_ACCENT = "#131F24"  # text and icons on a filled colour

BLUE = "#1CB0F6"
GREEN = "#58CC02"
PURPLE = "#CE82FF"
ORANGE = "#FF9600"
RED = "#FF4B4B"
YELLOW = "#FFC800"

SPEAK = BLUE
WORDS = PURPLE
TEACH = GREEN
SEE = ORANGE
RECORD = RED
GOOD = GREEN
OK = BLUE
NEUTRAL = MUTED
WARN = ORANGE

# Dictionary status -> (colour, icon, caption)
STATUS = {
    "verified": (GOOD, "check", "Verified"),
    "corroborated": (OK, "check2", "Likely"),
    "proposed": (NEUTRAL, "dot", "New"),
    "disputed": (WARN, "warning", "Unclear"),
}


def font(size: int, weight: str = "normal") -> tuple[str, int, str]:
    """weight: "normal", "bold" (semibold) or "heavy" (black, for headings and buttons)."""
    if weight == "heavy":
        return (FONT_HEAVY, size, "normal")
    if weight == "bold":
        return (FONT_STRONG, size, "normal")
    return (FONT, size, weight)


def _mix(colour: str, other: str, amount: float) -> str:
    a = [int(colour[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02x}" for x, y in zip(a, b))


def shade(colour: str, factor: float) -> str:
    """factor > 1: fade towards the background (2.0 = background), for tints.
    factor < 1: brighten (hover)."""
    if factor >= 1:
        return _mix(colour, BG, min(1.0, factor - 1))
    return _mix(colour, "#FFFFFF", 1 - factor)


def lip(colour: str) -> str:
    """The darker edge under a chunky button."""
    return _mix(colour, "#000000", 0.28)
