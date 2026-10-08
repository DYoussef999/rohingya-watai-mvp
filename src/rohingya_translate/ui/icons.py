"""Simple vector icons drawn on a Tk canvas, so they scale cleanly and need no image files.

Each icon is drawn in a box of ``size`` pixels centred on (cx, cy).
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


def round_rect(c: tk.Canvas, x1: float, y1: float, x2: float, y2: float, r: float, **kw):
    """A rounded rectangle (Tk has none built in)."""
    r = max(0.0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(points, smooth=True, **kw)


class _Pen:
    """Maps icon coordinates (-0.5..0.5) to canvas pixels."""

    def __init__(self, c: tk.Canvas, cx: float, cy: float, s: float, colour: str, tags,
                 knockout: str) -> None:
        self.c, self.cx, self.cy, self.s, self.colour, self.tags = c, cx, cy, s, colour, tags
        self.knockout = knockout  # colour for holes cut into filled shapes (lens, "!")
        self.w = max(2.0, s / 13)

    def p(self, *xy: float) -> list[float]:
        return [self.cx + v * self.s if i % 2 == 0 else self.cy + v * self.s
                for i, v in enumerate(xy)]

    def line(self, *xy: float, width: float | None = None, **kw) -> None:
        self.c.create_line(*self.p(*xy), fill=self.colour, width=width or self.w,
                           capstyle="round", joinstyle="round", tags=self.tags, **kw)

    def poly(self, *xy: float, fill: str | None = None, outline: str = "") -> None:
        self.c.create_polygon(*self.p(*xy), fill=fill or self.colour, outline=outline,
                              width=self.w, joinstyle="round", tags=self.tags)

    def oval(self, x1, y1, x2, y2, fill: str | None = "", outline: str | None = None) -> None:
        self.c.create_oval(*self.p(x1, y1, x2, y2), fill=fill if fill is not None else "",
                           outline=self.colour if outline is None else outline,
                           width=self.w, tags=self.tags)

    def arc(self, x1, y1, x2, y2, start: float, extent: float, **kw) -> None:
        self.c.create_arc(*self.p(x1, y1, x2, y2), start=start, extent=extent, style="arc",
                          outline=self.colour, width=self.w, tags=self.tags, **kw)

    def rrect(self, x1, y1, x2, y2, r: float, fill: str = "", outline: str | None = None):
        round_rect(self.c, *self.p(x1, y1, x2, y2), r * self.s, fill=fill,
                   outline=self.colour if outline is None else outline, width=self.w,
                   tags=self.tags)


def _mic(d: _Pen) -> None:
    d.rrect(-0.14, -0.44, 0.14, 0.12, 0.14, fill=d.colour)
    d.arc(-0.27, -0.16, 0.27, 0.27, 180, 180)
    d.line(0, 0.27, 0, 0.4)
    d.line(-0.15, 0.4, 0.15, 0.4)


def _speaker(d: _Pen) -> None:
    d.poly(-0.4, -0.12, -0.22, -0.12, -0.04, -0.3, -0.04, 0.3, -0.22, 0.12, -0.4, 0.12)
    d.arc(-0.2, -0.2, 0.2, 0.2, -50, 100)
    d.arc(-0.36, -0.36, 0.36, 0.36, -50, 100)


def _book(d: _Pen) -> None:
    d.poly(-0.42, -0.3, -0.03, -0.2, -0.03, 0.36, -0.42, 0.26, fill="", outline=d.colour)
    d.poly(0.42, -0.3, 0.03, -0.2, 0.03, 0.36, 0.42, 0.26, fill="", outline=d.colour)
    for y in (-0.08, 0.06):
        d.line(-0.32, y - 0.06, -0.13, y - 0.02, width=d.w * 0.7)
        d.line(0.32, y - 0.06, 0.13, y - 0.02, width=d.w * 0.7)


def _teach(d: _Pen) -> None:
    d.rrect(-0.42, -0.38, 0.42, 0.2, 0.14)
    d.poly(-0.2, 0.19, -0.3, 0.42, 0.04, 0.19)
    d.line(0, -0.24, 0, 0.06)
    d.line(-0.15, -0.09, 0.15, -0.09)


def _camera(d: _Pen) -> None:
    d.poly(-0.16, -0.2, -0.09, -0.33, 0.09, -0.33, 0.16, -0.2)
    d.rrect(-0.44, -0.22, 0.44, 0.32, 0.08, fill=d.colour)
    d.oval(-0.17, -0.12, 0.17, 0.22, fill=d.knockout, outline=d.knockout)
    d.oval(-0.08, -0.03, 0.08, 0.13, fill=d.colour, outline=d.colour)


def _check(d: _Pen) -> None:
    d.line(-0.32, 0.02, -0.08, 0.26, 0.34, -0.24, width=d.w * 1.6)


def _check2(d: _Pen) -> None:
    d.line(-0.42, 0.02, -0.24, 0.22, 0.08, -0.2, width=d.w * 1.3)
    d.line(-0.06, 0.08, 0.08, 0.22, 0.42, -0.2, width=d.w * 1.3)


def _dot(d: _Pen) -> None:
    d.oval(-0.16, -0.16, 0.16, 0.16, fill=d.colour)


def _warning(d: _Pen) -> None:
    d.poly(0, -0.42, 0.44, 0.36, -0.44, 0.36)
    d.c.create_line(*d.p(0, -0.14, 0, 0.12), fill=d.knockout, width=d.w * 1.2,
                    capstyle="round", tags=d.tags)
    d.oval(-0.03, 0.2, 0.03, 0.26, fill=d.knockout, outline=d.knockout)


def _stop(d: _Pen) -> None:
    d.rrect(-0.3, -0.3, 0.3, 0.3, 0.08, fill=d.colour)


def _folder(d: _Pen) -> None:
    d.poly(-0.44, -0.3, -0.12, -0.3, -0.04, -0.2, 0.44, -0.2, 0.44, 0.32, -0.44, 0.32,
           fill="", outline=d.colour)
    d.line(-0.44, -0.08, 0.44, -0.08)


def _gear(d: _Pen) -> None:
    import math

    for i in range(8):
        a = i * math.pi / 4
        d.line(0.24 * math.cos(a), 0.24 * math.sin(a), 0.4 * math.cos(a), 0.4 * math.sin(a),
               width=d.w * 1.6)
    d.oval(-0.27, -0.27, 0.27, 0.27, fill=d.colour)
    d.oval(-0.1, -0.1, 0.1, 0.1, fill=d.knockout, outline=d.knockout)


def _person(d: _Pen) -> None:
    d.oval(-0.15, -0.42, 0.15, -0.12, fill=d.colour)
    d.c.create_arc(*d.p(-0.34, -0.04, 0.34, 0.64), start=0, extent=180, style="chord",
                   fill=d.colour, outline=d.colour, tags=d.tags)


def _picture(d: _Pen) -> None:
    d.rrect(-0.44, -0.34, 0.44, 0.34, 0.06)
    d.oval(0.1, -0.24, 0.26, -0.08, fill=d.colour)
    d.poly(-0.36, 0.26, -0.1, -0.06, 0.06, 0.12, 0.16, 0.02, 0.36, 0.26)


def _search(d: _Pen) -> None:
    d.oval(-0.36, -0.36, 0.14, 0.14)
    d.line(0.1, 0.1, 0.38, 0.38, width=d.w * 1.5)


def _save(d: _Pen) -> None:
    d.line(0, -0.4, 0, 0.1)
    d.line(-0.17, -0.06, 0, 0.11, 0.17, -0.06)
    d.line(-0.4, 0.06, -0.4, 0.36, 0.4, 0.36, 0.4, 0.06)


def _redo(d: _Pen) -> None:
    d.arc(-0.32, -0.32, 0.32, 0.32, 60, 290)
    d.poly(0.14, -0.38, 0.36, -0.3, 0.2, -0.12)


def _close(d: _Pen) -> None:
    d.line(-0.25, -0.25, 0.25, 0.25, width=d.w * 1.3)
    d.line(-0.25, 0.25, 0.25, -0.25, width=d.w * 1.3)


def _play(d: _Pen) -> None:
    d.poly(-0.22, -0.32, 0.34, 0, -0.22, 0.32)


def _grid(d: _Pen) -> None:
    for x in (-0.38, 0.06):
        for y in (-0.38, 0.06):
            d.rrect(x, y, x + 0.32, y + 0.32, 0.06, fill=d.colour)


def _list(d: _Pen) -> None:
    for y in (-0.28, 0, 0.28):
        d.oval(-0.42, y - 0.06, -0.3, y + 0.06, fill=d.colour)
        d.line(-0.16, y, 0.42, y, width=d.w * 1.2)


ICONS: dict[str, Callable[[_Pen], None]] = {
    "mic": _mic, "speaker": _speaker, "book": _book, "teach": _teach, "camera": _camera,
    "check": _check, "check2": _check2, "dot": _dot, "warning": _warning, "stop": _stop,
    "folder": _folder, "gear": _gear, "person": _person, "picture": _picture,
    "search": _search, "save": _save, "redo": _redo, "close": _close, "play": _play,
    "grid": _grid, "list": _list,
}


def draw(c: tk.Canvas, name: str, cx: float, cy: float, size: float, colour: str,
         tags: str | tuple = (), knockout: str | None = None) -> None:
    """``knockout`` is the colour behind the icon, used for holes; defaults to the canvas's."""
    ICONS[name](_Pen(c, cx, cy, size, colour, tags, knockout or c.cget("bg")))
