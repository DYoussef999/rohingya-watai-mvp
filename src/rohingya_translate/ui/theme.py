"""Colours and fonts. Each section has its own colour so it can be recognised without reading."""

from __future__ import annotations

FONT = "Segoe UI"

BG = "#F5F1EA"  # warm paper
SURFACE = "#FFFFFF"
INK = "#1F2933"
MUTED = "#6B7280"
LINE = "#E3DDD3"
FAINT = "#ECE7DF"

SPEAK = "#0F766E"  # teal
WORDS = "#7C3AED"  # purple
TEACH = "#D97706"  # amber
SEE = "#2563EB"  # blue
RECORD = "#DC2626"  # red while recording
GOOD = "#16A34A"
OK = "#2563EB"
NEUTRAL = "#9CA3AF"
WARN = "#EA580C"

# Dictionary status -> (colour, icon, caption)
STATUS = {
    "verified": (GOOD, "check", "verified"),
    "corroborated": (OK, "check2", "likely"),
    "proposed": (NEUTRAL, "dot", "new"),
    "disputed": (WARN, "warning", "unclear"),
}


def font(size: int, weight: str = "normal") -> tuple[str, int, str]:
    return (FONT, size, weight)


def shade(colour: str, factor: float) -> str:
    """Darker (factor < 1) or lighter (factor > 1) version of a #RRGGBB colour."""
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    if factor < 1:
        r, g, b = (int(c * factor) for c in (r, g, b))
    else:
        r, g, b = (int(c + (255 - c) * (factor - 1)) for c in (r, g, b))
    return f"#{min(r, 255):02x}{min(g, 255):02x}{min(b, 255):02x}"
