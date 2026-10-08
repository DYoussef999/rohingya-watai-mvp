"""Desktop app for translating speech and growing the dictionary: ``rtranslate-gui``.

Visual first, because many users don't read English: big icons, one colour per
section, a press-to-talk microphone, and play buttons on every word. Built on
Tkinter (ships with Python). All model work runs on one background thread
(models are slow, and SQLite wants a single thread), and results are handed back
to the window.
"""

from __future__ import annotations

import queue
import threading
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rohingya_translate.config import DEFAULT_CONFIG, Config, load_config


class Worker:
    """Runs jobs one at a time on a background thread; results come back via ``poll``."""

    def __init__(self) -> None:
        self._jobs: queue.Queue = queue.Queue()
        self._results: queue.Queue = queue.Queue()
        threading.Thread(target=self._run, daemon=True).start()

    def submit(
        self,
        job: Callable[[], Any],
        on_done: Callable[[Any], None],
        on_error: Callable[[BaseException], None],
    ) -> None:
        self._jobs.put((job, on_done, on_error))

    def poll(self) -> None:
        """Call from the window's thread: delivers finished results to their callbacks."""
        while True:
            try:
                callback, value = self._results.get_nowait()
            except queue.Empty:
                return
            callback(value)

    def _run(self) -> None:
        while True:
            job, on_done, on_error = self._jobs.get()
            try:
                self._results.put((on_done, job()))
            except BaseException as e:  # noqa: BLE001 - shown to the user, not swallowed
                traceback.print_exc()
                self._results.put((on_error, e))


class Engine:
    """Pipeline and lexicon for one config, created on first use. Lives on the worker thread."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._pipeline = None
        self._lexicon = None

    def pipeline(self):
        from rohingya_translate.pipeline import Pipeline

        if self._pipeline is None:
            self._pipeline = Pipeline(self.config)
        return self._pipeline

    def lexicon(self, vision: bool = False):
        from rohingya_translate.lexicon import Lexicon

        if self._lexicon is None:
            self._lexicon = Lexicon.open(self.config)
        if vision and self._lexicon.labeler is None:
            self._lexicon.load_labeler(self.config.image_labeler)
        return self._lexicon

    def close(self) -> None:
        if self._lexicon is not None:
            self._lexicon.close()


class App:
    """The window: a colour-coded navigation bar and four screens."""

    def __init__(self, root, config_path: str, scale: float, demo: bool) -> None:
        import tkinter as tk

        from rohingya_translate.ui import screens
        from rohingya_translate.ui.theme import (
            BG,
            LINE,
            MUTED,
            ON_ACCENT,
            SEE,
            SPEAK,
            TEACH,
            WORDS,
            font,
        )
        from rohingya_translate.ui.widgets import IconButton, dark_title_bar

        self.root, self.s, self.demo = root, scale, demo
        self.config_path = config_path
        self.config = load_config(config_path)  # read-only copy for the window's thread
        self.worker = Worker()
        self._engine: Engine | None = None
        self.demo_files = None
        self._prompts: dict[str, Path] | None = None
        root.configure(bg=BG)
        dark_title_bar(root)

        header = tk.Frame(root, bg=BG, padx=int(20 * scale), pady=int(12 * scale))
        header.pack(fill="x")
        self.nav: dict[str, IconButton] = {}
        for name, icon, caption, colour in [("speak", "mic", "Speak", SPEAK),
                                            ("words", "book", "Words", WORDS),
                                            ("teach", "teach", "Teach", TEACH),
                                            ("see", "camera", "See", SEE)]:
            button = IconButton(header, icon, caption, lambda n=name: self.show(n),
                                colour=colour, size=40, filled=False, scale=scale,
                                font_size=13)
            button.pack(side="left", padx=(0, 12 * scale))
            self.nav[name] = button
        IconButton(header, "gear", "", self.settings, colour=MUTED, size=26, filled=False,
                   scale=scale).pack(side="right")
        if demo:
            tk.Label(header, text=" DEMO DATA ", font=font(11, "bold"), fg=ON_ACCENT, bg=TEACH,
                     padx=6, pady=4).pack(side="right", padx=12 * scale)

        tk.Frame(root, bg=LINE, height=1).pack(fill="x")
        self.body = tk.Frame(root, bg=BG)
        self.body.pack(fill="both", expand=True)
        self.status = tk.Label(root, text="", font=font(10), fg=MUTED, bg=BG, anchor="w",
                               padx=int(20 * scale), pady=int(4 * scale))
        self.status.pack(fill="x", side="bottom")

        self.speak = screens.SpeakScreen(self)
        self.words = screens.WordsScreen(self)
        self.teach = screens.TeachScreen(self)
        self.see = screens.SeeScreen(self)
        self.screens = {"speak": self.speak, "words": self.words, "teach": self.teach,
                        "see": self.see}
        self.current = ""
        self.show("speak")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._poll()
        if demo:
            self._start_demo()

    # plumbing

    def _poll(self) -> None:
        self.worker.poll()
        self.root.after(100, self._poll)

    def engine(self) -> Engine:
        """Worker thread only."""
        if self._engine is None:
            self._engine = Engine(load_config(self.config_path))
        return self._engine

    def run(self, label: str, job: Callable[[], Any], on_done: Callable[[Any], None],
            on_fail: Callable[[], None] | None = None) -> None:
        self.status.configure(text=f"{label}…   (the first time can take a while)")
        self.root.configure(cursor="watch")

        def done(value: Any) -> None:
            self.root.configure(cursor="")
            self.status.configure(text="")
            on_done(value)

        def failed(error: BaseException) -> None:
            self.root.configure(cursor="")
            self.status.configure(text="")
            if on_fail:
                on_fail()
            self.alert("error", f"{label} did not work:\n\n{error}")

        self.worker.submit(job, done, failed)

    def alert(self, kind: str, text: str) -> None:
        from rohingya_translate.ui import dialogs

        dialogs.alert(self.root, kind, text, self.s)

    def show(self, name: str) -> None:
        if self.current == name:
            return
        if self.current:
            self.screens[self.current].on_hide()
            self.screens[self.current].pack_forget()
        self.current = name
        for n, button in self.nav.items():
            button.set_selected(n == name)
        self.screens[name].pack(fill="both", expand=True)
        self.screens[name].on_show()

    def prompts(self) -> dict[str, Path]:
        from rohingya_translate.lexicon import list_prompts

        if self._prompts is None:
            self._prompts = list_prompts(self.config.lexicon.prompts)
        return self._prompts

    def picture_for(self, meaning: str) -> Path | None:
        return self.prompts().get(meaning)

    def play_clip(self, clip) -> None:
        from rohingya_translate.audio import load_wav
        from rohingya_translate.recorder import play

        try:
            play(load_wav(Path(self.words.clip_root) / clip.path))
        except (OSError, RuntimeError) as e:
            self.alert("error", str(e))

    def close(self) -> None:
        from rohingya_translate.recorder import stop_playback

        for screen in self.screens.values():
            screen.on_hide()
        stop_playback()
        if self._engine is not None:
            self.worker.submit(self._engine.close, lambda _: None, lambda _: None)
        self.root.after(200, self.root.destroy)

    # shared pieces

    def word_chip(self, master, entry):
        """A small card for a dictionary word: picture, word and status."""
        import tkinter as tk

        from rohingya_translate.ui.theme import INK, STATUS, SURFACE, font
        from rohingya_translate.ui.widgets import StatusBadge, picture_or_icon

        colour = STATUS[entry.status.value][0]
        chip = tk.Frame(master, bg=SURFACE, highlightbackground=colour,
                        highlightthickness=max(2, int(2 * self.s)), padx=8, pady=8)
        picture_or_icon(chip, self.picture_for(entry.meaning), int(64 * self.s), colour).pack()
        tk.Label(chip, text=entry.meaning, font=font(12, "bold"), fg=INK, bg=SURFACE).pack()
        StatusBadge(chip, entry.status.value, self.s, bg=SURFACE).pack(pady=(2, 0))
        return chip

    def word_details(self, entry, clips) -> None:
        """A window for one word: big picture, every speaker's recording, and photo checks."""
        import tkinter as tk

        from rohingya_translate.ui import dialogs
        from rohingya_translate.ui.theme import BG, INK, MUTED, SEE, STATUS, font
        from rohingya_translate.ui.widgets import (
            AgreementMeter,
            IconButton,
            StatusBadge,
            dark_title_bar,
            picture_or_icon,
            text_block,
        )

        s = self.s
        colour = STATUS[entry.status.value][0]
        win = tk.Toplevel(self.root, bg=BG, padx=int(24 * s), pady=int(20 * s))
        win.title(entry.meaning)
        win.transient(self.root)
        dark_title_bar(win)
        picture_or_icon(win, self.picture_for(entry.meaning), int(220 * s), colour, bg=BG).pack()
        tk.Label(win, text=entry.meaning, font=font(24, "bold"), fg=INK, bg=BG).pack(
            pady=(10 * s, 4 * s))
        StatusBadge(win, entry.status.value, s, bg=BG).pack()
        sp = entry.support
        AgreementMeter(win, sp.speakers, self.config.lexicon.min_speakers, sp.vision,
                       sp.conflicts, colour, s, bg=BG).pack(pady=(10 * s, 2 * s))
        text_block(win, f"{sp.speakers} of {self.config.lexicon.min_speakers} speakers agree"
                   + ("  ·  photo agrees" if sp.vision else "")
                   + (f"  ·  {sp.conflicts} disagree" if sp.conflicts else ""),
                   10, MUTED).pack()

        row = tk.Frame(win, bg=BG)
        row.pack(pady=(14 * s, 0))
        for clip in clips:
            IconButton(row, "speaker", clip.speaker_id, lambda c=clip: self.play_clip(c),
                       colour=colour, size=22, filled=False, layout="row", scale=s,
                       font_size=9).pack(side="left", padx=3)

        result = text_block(win, "", 11, MUTED)

        def check(camera: bool) -> None:
            from tkinter import filedialog

            if camera:
                image = dialogs.take_photo(self.root, s, SEE)
            else:
                path = filedialog.askopenfilename(parent=win, filetypes=[
                    ("Pictures", "*.jpg *.jpeg *.png *.bmp *.webp")])
                image = None
                if path:
                    from rohingya_translate.images import load_image

                    image = load_image(path)
            if image is None:
                return

            def job():
                lex = self.engine().lexicon(vision=True)
                return lex.check_image(entry.id, image), lex.vision_is_placeholder

            def done(value) -> None:
                v, placeholder = value
                text = "The photo agrees." if v.agrees else f"The photo looks like: {v.top_label}"
                if placeholder:
                    text += "\n(stand-in image model)"
                result.configure(text=text)
                self.words.refresh()

            self.run("Checking the photo", job, done)

        checks = tk.Frame(win, bg=BG)
        checks.pack(pady=(16 * s, 6 * s))
        IconButton(checks, "camera", "Check with camera", lambda: check(True), colour=SEE,
                   size=22, layout="row", scale=s, font_size=10).pack(side="left", padx=4)
        IconButton(checks, "folder", "Check with photo", lambda: check(False), colour=SEE,
                   size=22, filled=False, layout="row", scale=s, font_size=10).pack(
            side="left", padx=4)
        result.pack()

    def teach_word(self, meaning: str) -> None:
        self.show("teach")
        self.teach.meaning.set(meaning)

    def settings(self) -> None:
        """Choose the settings file (stub models, real models, or demo)."""
        import tkinter as tk
        from tkinter import filedialog

        from rohingya_translate.ui.theme import BG, GOOD, INK, MUTED, font
        from rohingya_translate.ui.widgets import IconButton, dark_title_bar, entry, text_block

        s = self.s
        win = tk.Toplevel(self.root, bg=BG, padx=int(24 * s), pady=int(20 * s))
        win.title("Settings")
        dark_title_bar(win)
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="Settings file", font=font(14, "bold"), fg=INK, bg=BG).pack(anchor="w")
        text_block(win, "default.toml: quick stand-ins.  models.toml: real models.  "
                        "demo.toml: made-up demo data.", 10, MUTED).pack(anchor="w", pady=(2, 8))
        path = tk.StringVar(value=self.config_path)
        row = tk.Frame(win, bg=BG)
        row.pack(fill="x")
        entry(row, path, 11, width=60).pack(side="left", fill="x", expand=True, ipady=3)

        def browse() -> None:
            chosen = filedialog.askopenfilename(parent=win, initialdir=Path(path.get()).parent,
                                                filetypes=[("Settings", "*.toml")])
            if chosen:
                path.set(chosen)

        IconButton(row, "folder", "", browse, colour=MUTED, size=20, filled=False,
                   scale=s).pack(side="left", padx=(8, 0))

        def apply() -> None:
            chosen = path.get()
            try:
                config = load_config(chosen)
            except (OSError, ValueError) as e:
                self.alert("error", f"Could not read that settings file:\n{e}")
                return
            win.destroy()
            old, self._engine = self._engine, None
            if old is not None:
                self.worker.submit(old.close, lambda _: None, lambda _: None)
            self.config_path, self.config, self._prompts = chosen, config, None
            self.teach.load_pictures()
            self.words.refresh()

        IconButton(win, "check", "Use these settings", apply, colour=GOOD, size=24,
                   layout="row", scale=s).pack(pady=(16, 0))

    def _start_demo(self) -> None:
        from rohingya_translate.demo import build_demo

        def done(files) -> None:
            self.demo_files, self._prompts = files, None
            self.speak.show_demo()
            self.see.show_demo()
            self.teach.load_pictures()
            self.teach.prefill_demo()
            self.words.refresh()

        self.run("Creating demo data",
                 lambda: build_demo(load_config(self.config_path), reset=True), done)


def main(argv: list[str] | None = None) -> None:
    import argparse
    import tkinter as tk

    parser = argparse.ArgumentParser(description="Rohingya Translate desktop app.")
    parser.add_argument("--config", help="settings file (default: configs/default.toml)")
    parser.add_argument("--demo", action="store_true",
                        help="rebuild the made-up demo data and open the app with it")
    args = parser.parse_args(argv)
    if args.demo:
        from rohingya_translate.demo import DEMO_CONFIG
    config_path = str(args.config or (DEMO_CONFIG if args.demo else DEFAULT_CONFIG))

    try:  # sharp text on high-resolution Windows screens instead of blurry scaling
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    root.title("Rohingya Translate (demo data)" if args.demo else "Rohingya Translate")
    scale = root.winfo_fpixels("1i") / 96  # sizes in the UI are for a 100% scaled screen
    root.geometry(f"{int(1080 * scale)}x{int(720 * scale)}")
    root.minsize(int(900 * scale), int(620 * scale))
    App(root, config_path, scale, args.demo)
    root.mainloop()


if __name__ == "__main__":
    main()
