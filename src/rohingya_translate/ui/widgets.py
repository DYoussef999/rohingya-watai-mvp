"""Visual building blocks: icon buttons, the microphone button, status badges and meters."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable
from pathlib import Path

import numpy as np

from rohingya_translate.ui import icons
from rohingya_translate.ui.theme import (
    BG,
    FAINT,
    GOOD,
    INK,
    LINE,
    MUTED,
    NEUTRAL,
    ON_ACCENT,
    RAISED,
    RECORD,
    STATUS,
    SURFACE,
    TEACH,
    WARN,
    font,
    shade,
)


class IconButton(tk.Canvas):
    """A rounded button with a big icon and an optional short caption.

    ``layout="column"`` puts the caption under the icon (tiles); ``"row"`` beside it (pills).
    """

    def __init__(self, master, icon: str, text: str = "", command: Callable | None = None,
                 colour: str = INK, size: int = 40, filled: bool = True, layout: str = "column",
                 scale: float = 1.0, bg: str | None = None, font_size: int = 12) -> None:
        self.icon, self.text, self.command, self.colour = icon, text, command, colour
        self.filled, self.layout, self.s = filled, layout, scale
        self.icon_px = size * scale
        self.font = tkfont.Font(family=font(1)[0], size=font_size, weight="bold")
        pad = 14 * scale
        text_w = self.font.measure(text) if text else 0
        text_h = self.font.metrics("linespace") if text else 0
        if layout == "column":
            width = max(self.icon_px + 2 * pad, text_w + 2 * pad)
            height = self.icon_px + pad * 2 + (text_h + 4 * scale if text else 0)
        else:
            width = self.icon_px + 2 * pad + (text_w + pad * 0.8 if text else 0)
            height = self.icon_px + pad * 1.4
        super().__init__(master, width=width, height=height, highlightthickness=0,
                         bg=bg or master.cget("bg"), cursor="hand2")
        self.w, self.h = width, height
        self.enabled, self.selected, self._hover = True, False, False
        self.bind("<Enter>", lambda _: self._set_hover(True))
        self.bind("<Leave>", lambda _: self._set_hover(False))
        self.bind("<ButtonRelease-1>", self._click)
        self._draw()

    def configure_button(self, *, icon: str | None = None, text: str | None = None,
                         colour: str | None = None) -> None:
        self.icon = icon or self.icon
        self.text = self.text if text is None else text
        self.colour = colour or self.colour
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._draw()

    def _set_hover(self, hover: bool) -> None:
        self._hover = hover
        self._draw()

    def _click(self, event) -> None:
        inside = 0 <= event.x <= self.w and 0 <= event.y <= self.h
        if inside and self.enabled and self.command:
            self.command()

    def _draw(self) -> None:
        self.delete("all")
        colour = self.colour if self.enabled else NEUTRAL
        if self.filled or self.selected:
            fill = shade(colour, 0.85) if self._hover and self.enabled else colour
            ink, outline = ON_ACCENT, ""
        else:
            fill = shade(colour, 1.82) if self._hover and self.enabled else SURFACE
            ink, outline = colour, shade(colour, 1.6)
        icons.round_rect(self, 1, 1, self.w - 1, self.h - 1, 16 * self.s, fill=fill,
                         outline=outline, width=max(1, int(2 * self.s)))
        pad = 14 * self.s
        if self.layout == "column":
            cy = pad + self.icon_px / 2
            icons.draw(self, self.icon, self.w / 2, cy, self.icon_px, ink, knockout=fill)
            if self.text:
                self.create_text(self.w / 2, self.h - pad * 0.9, text=self.text, fill=ink,
                                 font=self.font, anchor="s")
        else:
            cx = pad + self.icon_px / 2
            icons.draw(self, self.icon, cx, self.h / 2, self.icon_px, ink, knockout=fill)
            if self.text:
                self.create_text(cx + self.icon_px / 2 + pad * 0.6, self.h / 2, text=self.text,
                                 fill=ink, font=self.font, anchor="w")


class MicButton(tk.Canvas):
    """The big press-to-talk button. Shows a ring that grows with your voice, and a timer."""

    def __init__(self, master, colour: str, command: Callable, diameter: int = 150,
                 scale: float = 1.0) -> None:
        self.d = diameter * scale
        self.margin = 28 * scale
        size = self.d + 2 * self.margin
        super().__init__(master, width=size, height=size + 34 * scale, highlightthickness=0,
                         bg=master.cget("bg"), cursor="hand2")
        self.colour, self.command, self.s = colour, command, scale
        self.state, self.level, self.seconds = "idle", 0.0, 0.0
        self.bind("<ButtonRelease-1>", lambda _: self.state != "busy" and self.command())
        self._draw()

    def set_state(self, state: str) -> None:
        """"idle" (mic), "recording" (stop) or "busy" (thinking dots)."""
        self.state, self.level, self.seconds = state, 0.0, 0.0
        self.configure(cursor="watch" if state == "busy" else "hand2")
        self._draw()

    def set_level(self, level: float, seconds: float) -> None:
        self.level, self.seconds = level, seconds
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        c = self.margin + self.d / 2
        r = self.d / 2
        if self.state == "recording":
            ring = r + 4 * self.s + self.level * (self.margin - 4 * self.s)
            self.create_oval(c - ring, c - ring, c + ring, c + ring, fill=shade(RECORD, 1.75),
                             outline="")
            self.create_oval(c - r, c - r, c + r, c + r, fill=RECORD, outline="")
            icons.draw(self, "stop", c, c, self.d * 0.36, ON_ACCENT, knockout=RECORD)
            minutes, secs = divmod(int(self.seconds), 60)
            self.create_text(c, self.d + 2 * self.margin + 12 * self.s,
                             text=f"{minutes}:{secs:02d}", fill=RECORD, font=font(14, "bold"))
        elif self.state == "busy":
            self.create_oval(c - r, c - r, c + r, c + r, fill=FAINT, outline="")
            for i in range(3):
                x = c + (i - 1) * r * 0.42
                self.create_oval(x - 9 * self.s, c - 9 * self.s, x + 9 * self.s, c + 9 * self.s,
                                 fill=self.colour, outline="")
        else:
            self.create_oval(c - r - 6 * self.s, c - r - 6 * self.s, c + r + 6 * self.s,
                             c + r + 6 * self.s, fill=shade(self.colour, 1.8), outline="")
            self.create_oval(c - r, c - r, c + r, c + r, fill=self.colour, outline="")
            icons.draw(self, "mic", c, c, self.d * 0.55, ON_ACCENT, knockout=self.colour)


class StatusBadge(tk.Canvas):
    """Coloured pill: icon + one word. Colour and icon carry the meaning; the word helps helpers."""

    def __init__(self, master, status: str, scale: float = 1.0, bg: str | None = None) -> None:
        colour, icon, caption = STATUS[status]
        f = tkfont.Font(family=font(1)[0], size=10, weight="bold")
        h = 26 * scale
        w = h + f.measure(caption) + 12 * scale
        super().__init__(master, width=w, height=h, highlightthickness=0,
                         bg=bg or master.cget("bg"))
        tint = shade(colour, 1.78)  # soft pill, bright icon and word: calmer on a dark screen
        icons.round_rect(self, 0, 0, w, h, h / 2, fill=tint, outline="")
        icons.draw(self, icon, h / 2 + 2 * scale, h / 2, h * 0.62, colour, knockout=tint)
        self.create_text(h + 2 * scale, h / 2, text=caption, fill=colour, font=f, anchor="w")


class AgreementMeter(tk.Canvas):
    """People icons filling up towards "verified", plus a camera if a photo agreed.

    Orange people are speakers who gave this word a different meaning.
    """

    def __init__(self, master, speakers: int, needed: int, vision: bool, conflicts: int,
                 colour: str, scale: float = 1.0, bg: str | None = None) -> None:
        icon = 22 * scale
        slots = max(needed, speakers)
        count = slots + conflicts + (1 if vision else 0)
        super().__init__(master, width=max(1, count) * (icon + 3 * scale), height=icon + 4,
                         highlightthickness=0, bg=bg or master.cget("bg"))
        x = icon / 2
        for i in range(slots):
            icons.draw(self, "person", x, icon / 2 + 2, icon, colour if i < speakers else LINE)
            x += icon + 3 * scale
        if vision:
            icons.draw(self, "camera", x, icon / 2 + 2, icon * 0.95, colour, )
            x += icon + 3 * scale
        for _ in range(conflicts):
            icons.draw(self, "person", x, icon / 2 + 2, icon, WARN)
            x += icon + 3 * scale


class ConfidenceDots(tk.Canvas):
    """Five dots: how sure the translator is. Green when sure, orange when unsure."""

    def __init__(self, master, confidence: float | None, scale: float = 1.0) -> None:
        r = 8 * scale
        super().__init__(master, width=5 * (2 * r + 6 * scale), height=2 * r + 4,
                         highlightthickness=0, bg=master.cget("bg"))
        value = confidence or 0.0
        filled = round(value * 5)
        colour = GOOD if value >= 0.7 else TEACH if value >= 0.4 else WARN
        for i in range(5):
            x = r + i * (2 * r + 6 * scale)
            self.create_oval(x - r, 2, x + r, 2 + 2 * r, outline="",
                             fill=colour if i < filled else LINE)


class Waveform(tk.Canvas):
    """Bars showing a recording's loudness over time, so speakers can see it was captured."""

    def __init__(self, master, width: int, height: int, colour: str) -> None:
        super().__init__(master, width=width, height=height, highlightthickness=0,
                         bg=master.cget("bg"))
        self.colour, self.w, self.h = colour, width, height
        self.show(None)

    def show(self, samples: np.ndarray | None) -> None:
        self.delete("all")
        bars = 48
        step = self.w / bars
        if samples is None or len(samples) < bars:
            for i in range(bars):
                x = i * step + step / 2
                self.create_line(x, self.h / 2 - 2, x, self.h / 2 + 2, fill=LINE,
                                 width=max(2, step * 0.5), capstyle="round")
            return
        chunks = np.array_split(np.abs(samples), bars)
        peaks = np.array([c.max() if len(c) else 0 for c in chunks])
        peaks = peaks / (peaks.max() or 1)
        for i, p in enumerate(peaks):
            x = i * step + step / 2
            half = max(2, p * (self.h / 2 - 3))
            self.create_line(x, self.h / 2 - half, x, self.h / 2 + half, fill=self.colour,
                             width=max(2, step * 0.5), capstyle="round")


class ThinScrollbar(tk.Canvas):
    """A slim rounded scrollbar (the native Windows one can't be coloured)."""

    def __init__(self, master, command: Callable, bg: str, width: int = 10) -> None:
        super().__init__(master, width=width, bg=bg, highlightthickness=0)
        self.command, self.first, self.last = command, 0.0, 1.0
        self._drag: tuple[int, float] | None = None
        self._hover = False
        self.bind("<Configure>", lambda _: self._draw())
        self.bind("<Enter>", lambda _: self._set_hover(True))
        self.bind("<Leave>", lambda _: self._set_hover(False))
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._move)

    def set(self, first: str, last: str) -> None:
        self.first, self.last = float(first), float(last)
        self._draw()

    def _set_hover(self, hover: bool) -> None:
        self._hover = hover
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        if self.last - self.first >= 0.999:
            return  # everything fits: no bar
        w, h = self.winfo_width(), self.winfo_height()
        icons.round_rect(self, 2, self.first * h + 2, w - 2, self.last * h - 2, w / 2,
                         fill=MUTED if self._hover else LINE, outline="")

    def _press(self, event) -> None:
        h = max(1, self.winfo_height())
        if not self.first * h <= event.y <= self.last * h:  # click outside the thumb: jump
            self.command("moveto", event.y / h - (self.last - self.first) / 2)
        self._drag = (event.y, self.first)

    def _move(self, event) -> None:
        if self._drag:
            y0, first0 = self._drag
            self.command("moveto", first0 + (event.y - y0) / max(1, self.winfo_height()))


class ScrollFrame(tk.Frame):
    """A vertically scrolling area; put content in ``.inner``."""

    def __init__(self, master, bg: str = BG) -> None:
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        bar = ThinScrollbar(self, self.canvas.yview, bg=bg)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda _: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._window, width=e.width))
        self.canvas.bind("<Enter>", lambda _: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda _: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def scroll_to(self, widget: tk.Widget) -> None:
        self.update_idletasks()
        total = max(1, self.inner.winfo_height())
        self.canvas.yview_moveto(max(0.0, (widget.winfo_y() - 20) / total))


_PICTURES: dict[tuple[str, int], tk.PhotoImage] = {}


def load_picture(path: str | Path, max_px: int) -> tk.PhotoImage | None:
    """A picture file as a Tk image no larger than ``max_px``, or None. Cached."""
    key = (str(path), max_px)
    if key in _PICTURES:
        return _PICTURES[key]
    image = None
    try:
        from rohingya_translate.images import load_image, to_png_base64

        rgb = load_image(path)
        h, w = rgb.shape[:2]
        if h > w:  # fit the long side
            import cv2

            rgb = cv2.resize(rgb, (round(w * max_px / h), max_px), interpolation=cv2.INTER_AREA)
        image = tk.PhotoImage(data=to_png_base64(rgb, max_width=max_px))
    except ImportError:  # no OpenCV: Tk reads PNG and GIF itself, shrinking by whole steps
        if str(path).lower().endswith((".png", ".gif")):
            image = tk.PhotoImage(file=str(path))
            factor = max(1, -(-max(image.width(), image.height()) // max_px))
            image = image.subsample(factor)
    except (ValueError, OSError, tk.TclError):
        image = None
    _PICTURES[key] = image
    return image


def picture_or_icon(master, path: Path | None, size: int, colour: str,
                    bg: str = SURFACE) -> tk.Widget:
    """The picture for a word, or a placeholder picture icon if there is none."""
    image = load_picture(path, size) if path else None
    if image is not None:
        label = tk.Label(master, image=image, bg=bg, borderwidth=0)
        label.image = image
        return label
    canvas = tk.Canvas(master, width=size, height=size, bg=bg, highlightthickness=0)
    icons.round_rect(canvas, 2, 2, size - 2, size - 2, size * 0.12, fill=shade(colour, 1.85),
                     outline="")
    icons.draw(canvas, "picture", size / 2, size / 2, size * 0.5, shade(colour, 1.4))
    return canvas


def entry(master, var: tk.StringVar, size: int = 12, width: int | None = None,
          accent: str = MUTED) -> tk.Entry:
    """A dark text box with a thin border that lights up while typing."""
    extra = {"width": width} if width else {}
    return tk.Entry(master, textvariable=var, font=font(size), bg=RAISED, fg=INK,
                    insertbackground=INK, relief="flat", highlightthickness=1,
                    highlightbackground=LINE, highlightcolor=accent,
                    selectbackground=shade(accent, 1.5), selectforeground=INK, **extra)


def dark_title_bar(window: tk.Misc) -> None:
    """Ask Windows 10/11 for a dark title bar to match the theme. Ignored elsewhere."""
    try:
        import ctypes

        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1)
        for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE: new id, then old one
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except (AttributeError, OSError):
        pass


def text_block(master, text: str, size: int = 12, colour: str = MUTED, bg: str = BG,
               wrap: int = 600, weight: str = "normal") -> tk.Label:
    return tk.Label(master, text=text, font=font(size, weight), fg=colour, bg=bg,
                    wraplength=wrap, justify="left", anchor="w")
