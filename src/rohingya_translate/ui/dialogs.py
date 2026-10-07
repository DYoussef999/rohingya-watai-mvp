"""Pop-up windows: messages with big icons, the webcam preview, and a voice recorder."""

from __future__ import annotations

import tkinter as tk

from rohingya_translate.audio import Audio
from rohingya_translate.recorder import Recorder
from rohingya_translate.ui import icons
from rohingya_translate.ui.theme import BG, GOOD, INK, MUTED, SEE, WARN, font
from rohingya_translate.ui.widgets import IconButton, MicButton

KINDS = {"error": ("warning", WARN), "done": ("check", GOOD), "info": ("picture", SEE)}


def _dialog(root: tk.Tk, title: str) -> tk.Toplevel:
    win = tk.Toplevel(root, bg=BG, padx=24, pady=20)
    win.title(title)
    win.transient(root)
    win.resizable(False, False)
    win.grab_set()
    return win


def _centre(root: tk.Tk, win: tk.Toplevel) -> None:
    win.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - win.winfo_width()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - win.winfo_height()) // 3
    win.geometry(f"+{max(0, x)}+{max(0, y)}")


def alert(root: tk.Tk, kind: str, text: str, scale: float = 1.0) -> None:
    """A message led by a big coloured icon, so its tone is clear before reading it."""
    icon, colour = KINDS[kind]
    win = _dialog(root, "Rohingya Translate")
    size = 72 * scale
    c = tk.Canvas(win, width=size, height=size, bg=BG, highlightthickness=0)
    icons.draw(c, icon, size / 2, size / 2, size * 0.9, colour)
    c.pack()
    tk.Label(win, text=text, font=font(13), fg=INK, bg=BG, wraplength=int(420 * scale),
             justify="center").pack(pady=(10, 16))
    IconButton(win, "check", "OK", win.destroy, colour=colour, size=26, layout="row",
               scale=scale).pack()
    _centre(root, win)
    win.wait_window()


def take_photo(root: tk.Tk, scale: float = 1.0, colour: str = SEE):
    """Live webcam preview; returns the photo (RGB array), or None if cancelled."""
    try:
        from rohingya_translate.images import Camera, exposure_settled, to_png_base64

        camera = Camera()
    except (ImportError, RuntimeError) as e:
        alert(root, "error", str(e), scale)
        return None

    win = _dialog(root, "Webcam")
    view = tk.Label(win, bg="black", width=int(40 * scale), height=int(12 * scale))
    view.pack()
    row = tk.Frame(win, bg=BG, pady=14)
    row.pack()
    shot = {"latest": None, "taken": None, "open": True}
    brightness: list[float] = []

    def close(take: bool) -> None:
        if take:
            shot["taken"] = shot["latest"]
        shot["open"] = False
        win.destroy()

    take = IconButton(row, "camera", "Take photo", lambda: close(True), colour=colour, size=34,
                      layout="row", scale=scale)
    take.set_enabled(False)
    take.pack(side="left", padx=6)
    IconButton(row, "close", "Cancel", lambda: close(False), colour=MUTED, size=24,
               filled=False, layout="row", scale=scale).pack(side="left", padx=6)
    win.protocol("WM_DELETE_WINDOW", lambda: close(False))

    def tick() -> None:
        if not shot["open"]:
            return
        frame = camera.read()
        if frame is not None:
            shot["latest"] = frame
            brightness.append(float(frame.mean()))
            if not take.enabled and (exposure_settled(brightness) or len(brightness) > 90):
                take.set_enabled(True)  # only once the camera has adjusted to the light
            picture = tk.PhotoImage(data=to_png_base64(frame, max_width=int(560 * scale)))
            view.configure(image=picture, width=picture.width(), height=picture.height())
            view.image = picture
        win.after(30, tick)

    _centre(root, win)
    tick()
    win.wait_window()
    camera.close()
    return shot["taken"]


def record(root: tk.Tk, prompt: str, colour: str, scale: float = 1.0) -> Audio | None:
    """Ask for a spoken word: tap the mic, speak, tap again. Returns None if cancelled."""
    win = _dialog(root, "Speak")
    tk.Label(win, text=prompt, font=font(14, "bold"), fg=INK, bg=BG).pack(pady=(0, 6))
    recorder = Recorder()
    result: dict[str, Audio | None] = {"audio": None}

    def tick() -> None:
        if recorder.recording:
            mic.set_level(recorder.level, recorder.elapsed)
            win.after(50, tick)

    def toggle() -> None:
        if recorder.recording:
            result["audio"] = recorder.stop()
            win.destroy()
            return
        try:
            recorder.start()
        except RuntimeError as e:
            win.destroy()
            alert(root, "error", str(e), scale)
            return
        mic.set_state("recording")
        tick()

    def cancel() -> None:
        if recorder.recording:
            recorder.stop()
        win.destroy()

    mic = MicButton(win, colour, toggle, diameter=120, scale=scale)
    mic.pack()
    IconButton(win, "close", "Cancel", cancel, colour=MUTED, size=22, filled=False,
               layout="row", scale=scale).pack(pady=(4, 0))
    win.protocol("WM_DELETE_WINDOW", cancel)
    _centre(root, win)
    win.wait_window()
    return result["audio"]
