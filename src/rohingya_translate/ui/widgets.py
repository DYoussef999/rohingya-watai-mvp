"""Visual building blocks: chunky buttons, the microphone, navigation, badges and meters."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable
from pathlib import Path

import numpy as np

from rohingya_translate.ui import icons
from rohingya_translate.ui.theme import (
    BG,
    BLUE,
    INK,
    LINE,
    MUTED,
    NEUTRAL,
    ON_ACCENT,
    RAISED,
    RECORD,
    STATUS,
    SURFACE,
    WARN,
    font,
    lip,
    shade,
)


class IconButton(tk.Canvas):
    """A chunky rounded button with a darker edge underneath that "presses down" when clicked.

    ``filled`` buttons are the main action (colour fill, dark label). Others are outlined.
    ``layout="column"`` puts the label under the icon; ``"row"`` beside it. ``icon`` may be
    empty for a text-only button. ``upper`` writes the label in capitals, Duolingo style.
    """

    def __init__(self, master, icon: str, text: str = "", command: Callable | None = None,
                 colour: str = BLUE, size: int = 40, filled: bool = True, layout: str = "column",
                 scale: float = 1.0, bg: str | None = None, font_size: int = 12,
                 upper: bool = False, min_width: int = 0) -> None:
        self.icon, self.command, self.colour = icon, command, colour
        self.text = text.upper() if upper else text
        self.filled, self.layout, self.s = filled, layout, scale
        self.icon_px = size * scale if icon else 0
        self.lip = 4 * scale
        self.font = tkfont.Font(family=font(1, "heavy" if upper else "bold")[0],
                                size=font_size)
        pad = 14 * scale
        text_w = self.font.measure(self.text) if self.text else 0
        text_h = self.font.metrics("linespace") if self.text else 0
        if layout == "column":
            width = max(self.icon_px + 2 * pad, text_w + 2 * pad)
            height = self.icon_px + pad * 2 + (text_h + 4 * scale if self.text else 0)
        else:
            gap = pad * 0.7 if icon and self.text else 0
            width = self.icon_px + gap + text_w + 2 * pad * (1.3 if upper else 1)
            height = max(self.icon_px, text_h) + pad * 1.5
        width = max(width, min_width * scale)
        super().__init__(master, width=width, height=height + self.lip, highlightthickness=0,
                         bg=bg or master.cget("bg"), cursor="hand2")
        self.w, self.h = width, height
        self.enabled, self.selected, self._hover, self._down = True, False, False, False
        self.bind("<Enter>", lambda _: self._set(hover=True))
        self.bind("<Leave>", lambda _: self._set(hover=False, down=False))
        self.bind("<ButtonPress-1>", lambda _: self._set(down=True))
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

    def _set(self, hover: bool | None = None, down: bool | None = None) -> None:
        self._hover = self._hover if hover is None else hover
        self._down = self._down if down is None else down
        self._draw()

    def _click(self, event) -> None:
        self._set(down=False)
        inside = 0 <= event.x <= self.w and 0 <= event.y <= self.h + self.lip
        if inside and self.enabled and self.command:
            self.command()

    def _draw(self) -> None:
        self.delete("all")
        r = 14 * self.s
        if not self.enabled:
            face, edge, ink, border = RAISED, RAISED, MUTED, ""
        elif self.filled or self.selected:
            face = shade(self.colour, 0.9) if self._hover else self.colour
            edge, ink, border = lip(self.colour), ON_ACCENT, ""
        else:
            face = RAISED if self._hover else self.cget("bg")
            edge, ink, border = LINE, self.colour, LINE
        down = self.lip if self._down and self.enabled else 0
        if self.enabled:  # the edge underneath; disappears while pressed
            icons.round_rect(self, 1, self.lip, self.w - 1, self.h + self.lip - 1, r,
                             fill=edge, outline="")
        icons.round_rect(self, 1, 1 + down, self.w - 1, self.h - 1 + down, r, fill=face,
                         outline=border, width=max(1, int(2 * self.s)))
        pad = 14 * self.s
        if self.layout == "column":
            cy = pad + self.icon_px / 2 + down
            if self.icon:
                icons.draw(self, self.icon, self.w / 2, cy, self.icon_px, ink, knockout=face)
            if self.text:
                self.create_text(self.w / 2, self.h - pad * 0.9 + down, text=self.text, fill=ink,
                                 font=self.font, anchor="s")
        else:
            gap = pad * 0.7 if self.icon and self.text else 0
            content = self.icon_px + gap + (self.font.measure(self.text) if self.text else 0)
            x = (self.w - content) / 2
            if self.icon:
                icons.draw(self, self.icon, x + self.icon_px / 2, self.h / 2 + down,
                           self.icon_px, ink, knockout=face)
            if self.text:
                self.create_text(x + self.icon_px + gap, self.h / 2 + down, text=self.text,
                                 fill=ink, font=self.font, anchor="w")


def link(master, text: str, command: Callable, colour: str = BLUE, size: int = 11,
         bg: str | None = None) -> tk.Label:
    """A quiet text button for secondary actions."""
    label = tk.Label(master, text=text.upper(), font=font(size, "heavy"), fg=colour,
                     bg=bg or master.cget("bg"), cursor="hand2")
    label.bind("<Button-1>", lambda _: command())
    label.bind("<Enter>", lambda _: label.configure(fg=shade(colour, 0.75)))
    label.bind("<Leave>", lambda _: label.configure(fg=colour))
    return label


class NavItem(tk.Canvas):
    """One entry in the sidebar: coloured icon and a word. The current one is highlighted."""

    def __init__(self, master, icon: str, text: str, colour: str, command: Callable,
                 width: int, scale: float = 1.0) -> None:
        self.h = 56 * scale
        super().__init__(master, width=width, height=self.h, highlightthickness=0,
                         bg=master.cget("bg"), cursor="hand2")
        self.icon, self.text, self.colour, self.s, self.w = icon, text, colour, scale, width
        self.selected, self._hover = False, False
        self.bind("<Enter>", lambda _: self._set_hover(True))
        self.bind("<Leave>", lambda _: self._set_hover(False))
        self.bind("<ButtonRelease-1>", lambda _: command())
        self._draw()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._draw()

    def _set_hover(self, hover: bool) -> None:
        self._hover = hover
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        s = self.s
        if self.selected:
            icons.round_rect(self, 2, 2, self.w - 2, self.h - 2, 14 * s,
                             fill=shade(BLUE, 1.82), outline=BLUE, width=max(1, int(2 * s)))
        elif self._hover:
            icons.round_rect(self, 2, 2, self.w - 2, self.h - 2, 14 * s, fill=RAISED, outline="")
        icons.draw(self, self.icon, 30 * s, self.h / 2, 30 * s, self.colour)
        self.create_text(58 * s, self.h / 2, text=self.text.upper(), anchor="w",
                         font=font(13, "heavy"), fill=BLUE if self.selected else INK)


class Segmented(tk.Frame):
    """A two-or-more way switch, e.g. Cards | Table."""

    def __init__(self, master, options: list[tuple[str, str, str]], command: Callable[[str], None],
                 scale: float = 1.0) -> None:
        super().__init__(master, bg=master.cget("bg"))
        self.buttons: dict[str, IconButton] = {}
        for key, icon, text in options:
            b = IconButton(self, icon, text, lambda k=key: (self.select(k), command(k)),
                           colour=BLUE, size=18, filled=False, layout="row", scale=scale,
                           font_size=10, upper=True)
            b.pack(side="left", padx=(0, 6 * scale))
            self.buttons[key] = b

    def select(self, key: str) -> None:
        for k, b in self.buttons.items():
            b.set_selected(k == key)


class ProgressBar(tk.Canvas):
    """A rounded lesson progress bar."""

    def __init__(self, master, width: int, colour: str, scale: float = 1.0,
                 height: int = 16) -> None:
        self.h = height * scale
        super().__init__(master, width=width, height=self.h, highlightthickness=0,
                         bg=master.cget("bg"))
        self.colour, self.w = colour, width
        self.bind("<Configure>", lambda e: self._resize(e.width))
        self.value = 0.0
        self.set(0.0)

    def _resize(self, width: int) -> None:
        self.w = width
        self.set(self.value)

    def set(self, value: float) -> None:
        self.value = value
        self.delete("all")
        icons.round_rect(self, 0, 0, self.w, self.h, self.h / 2, fill=RAISED, outline="")
        if value > 0:
            end = max(self.h, self.w * min(1.0, value))
            icons.round_rect(self, 0, 0, end, self.h, self.h / 2, fill=self.colour, outline="")
            icons.round_rect(self, self.h * 0.5, self.h * 0.22, end - self.h * 0.5,
                             self.h * 0.45, self.h * 0.12, fill=shade(self.colour, 0.75),
                             outline="")  # the little highlight Duolingo bars have


class MicButton(tk.Canvas):
    """The big press-to-talk button, with a chunky edge. Shows a ring that grows with your voice."""

    def __init__(self, master, colour: str, command: Callable, diameter: int = 150,
                 scale: float = 1.0) -> None:
        self.d = diameter * scale
        self.margin = 24 * scale
        self.lip = 7 * scale
        size = self.d + 2 * self.margin
        super().__init__(master, width=size, height=size + self.lip + 30 * scale,
                         highlightthickness=0, bg=master.cget("bg"), cursor="hand2")
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
        colour = {"recording": RECORD, "busy": RAISED}.get(self.state, self.colour)
        if self.state == "recording":
            ring = r + 4 * self.s + self.level * (self.margin - 4 * self.s)
            self.create_oval(c - ring, c - ring, c + ring, c + ring, fill=shade(RECORD, 1.7),
                             outline="")
        self.create_oval(c - r, c - r + self.lip, c + r, c + r + self.lip,
                         fill=lip(colour) if self.state != "busy" else LINE, outline="")
        self.create_oval(c - r, c - r, c + r, c + r, fill=colour, outline="")
        if self.state == "recording":
            icons.draw(self, "stop", c, c, self.d * 0.34, ON_ACCENT, knockout=colour)
            minutes, secs = divmod(int(self.seconds), 60)
            self.create_text(c, self.d + 2 * self.margin + self.lip + 8 * self.s,
                             text=f"{minutes}:{secs:02d}", fill=RECORD, font=font(14, "heavy"))
        elif self.state == "busy":
            for i in range(3):
                x = c + (i - 1) * r * 0.42
                self.create_oval(x - 9 * self.s, c - 9 * self.s, x + 9 * self.s, c + 9 * self.s,
                                 fill=self.colour, outline="")
        else:
            icons.draw(self, "mic", c, c, self.d * 0.52, ON_ACCENT, knockout=colour)


class Pill(tk.Canvas):
    """A soft coloured pill: icon + a word or two. The colour and icon carry the meaning."""

    def __init__(self, master, icon: str, caption: str, colour: str, scale: float = 1.0,
                 bg: str | None = None, size: int = 9) -> None:
        f = tkfont.Font(family=font(1, "heavy")[0], size=size)
        caption = caption.upper()
        h = (26 + (size - 9) * 2) * scale
        w = h + f.measure(caption) + 12 * scale
        super().__init__(master, width=w, height=h, highlightthickness=0,
                         bg=bg or master.cget("bg"))
        tint = shade(colour, 1.8)
        icons.round_rect(self, 0, 0, w, h, h / 2, fill=tint, outline="")
        icons.draw(self, icon, h / 2 + 2 * scale, h / 2, h * 0.6, colour, knockout=tint)
        self.create_text(h + 2 * scale, h / 2, text=caption, fill=colour, font=f, anchor="w")


class StatusBadge(Pill):
    """The pill for a dictionary status (verified, likely, new, unclear)."""

    def __init__(self, master, status: str, scale: float = 1.0, bg: str | None = None) -> None:
        colour, icon, caption = STATUS[status]
        super().__init__(master, icon, caption, colour, scale, bg)


class AgreementMeter(tk.Canvas):
    """People icons filling up towards "verified", plus a camera if a photo agreed.

    Orange people are speakers who gave this word a different meaning.
    """

    def __init__(self, master, speakers: int, needed: int, vision: bool, conflicts: int,
                 colour: str, scale: float = 1.0, bg: str | None = None) -> None:
        icon = 24 * scale
        slots = max(needed, speakers)
        count = slots + conflicts + (1 if vision else 0)
        super().__init__(master, width=max(1, count) * (icon + 4 * scale), height=icon + 4,
                         highlightthickness=0, bg=bg or master.cget("bg"))
        x = icon / 2
        for i in range(slots):
            icons.draw(self, "person", x, icon / 2 + 2, icon, colour if i < speakers else LINE)
            x += icon + 4 * scale
        if vision:
            icons.draw(self, "camera", x, icon / 2 + 2, icon * 0.95, colour)
            x += icon + 4 * scale
        for _ in range(conflicts):
            icons.draw(self, "person", x, icon / 2 + 2, icon, WARN)
            x += icon + 4 * scale


class Waveform(tk.Canvas):
    """Bars showing a recording's loudness over time, so speakers can see it was captured."""

    def __init__(self, master, width: int, height: int, colour: str) -> None:
        super().__init__(master, width=width, height=height, highlightthickness=0,
                         bg=master.cget("bg"))
        self.colour, self.w, self.h = colour, width, height
        self.show(None)

    def show(self, samples: np.ndarray | None) -> None:
        self.delete("all")
        bars = 40
        step = self.w / bars
        if samples is None or len(samples) < bars:
            for i in range(bars):
                x = i * step + step / 2
                self.create_line(x, self.h / 2 - 2, x, self.h / 2 + 2, fill=LINE,
                                 width=max(3, step * 0.55), capstyle="round")
            return
        chunks = np.array_split(np.abs(samples), bars)
        peaks = np.array([c.max() if len(c) else 0 for c in chunks])
        peaks = peaks / (peaks.max() or 1)
        for i, p in enumerate(peaks):
            x = i * step + step / 2
            half = max(2, p * (self.h / 2 - 3))
            self.create_line(x, self.h / 2 - half, x, self.h / 2 + half, fill=self.colour,
                             width=max(3, step * 0.55), capstyle="round")


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
    icons.round_rect(canvas, 2, 2, size - 2, size - 2, size * 0.12, fill=RAISED, outline="")
    icons.draw(canvas, "picture", size / 2, size / 2, size * 0.45, NEUTRAL)
    return canvas


def entry(master, var: tk.StringVar, size: int = 12, width: int | None = None,
          accent: str = BLUE) -> tk.Entry:
    """A dark, rounded-looking text box with a border that lights up while typing."""
    extra = {"width": width} if width else {}
    return tk.Entry(master, textvariable=var, font=font(size), bg=RAISED, fg=INK,
                    insertbackground=INK, relief="flat", highlightthickness=2,
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
