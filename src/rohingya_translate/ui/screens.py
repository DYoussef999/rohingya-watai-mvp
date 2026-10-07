"""The four screens: Speak (translate), Words (dictionary), Teach (add a word) and See (photos).

Visual first: every action is a big icon, every status a colour, every word playable.
English captions are short and aimed at the helper or caseworker.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING, Any

from rohingya_translate.audio import Audio, load_wav
from rohingya_translate.recorder import Recorder, play
from rohingya_translate.ui import dialogs, icons
from rohingya_translate.ui.theme import (
    BG,
    GOOD,
    INK,
    LINE,
    MUTED,
    SEE,
    SPEAK,
    STATUS,
    SURFACE,
    TEACH,
    WARN,
    WORDS,
    font,
    shade,
)
from rohingya_translate.ui.widgets import (
    AgreementMeter,
    ConfidenceDots,
    IconButton,
    MicButton,
    ScrollFrame,
    StatusBadge,
    Waveform,
    picture_or_icon,
    text_block,
)

if TYPE_CHECKING:
    from rohingya_translate.app import App

AUDIO_TYPES = [("WAV recordings", "*.wav"), ("All files", "*.*")]
IMAGE_TYPES = [("Pictures", "*.jpg *.jpeg *.png *.bmp *.webp"), ("All files", "*.*")]
MIN_SECONDS = 0.3


def title_row(master, icon: str, title: str, colour: str, scale: float) -> tk.Frame:
    row = tk.Frame(master, bg=BG)
    size = 44 * scale
    c = tk.Canvas(row, width=size, height=size, bg=BG, highlightthickness=0)
    icons.draw(c, icon, size / 2, size / 2, size * 0.85, colour)
    c.pack(side="left")
    tk.Label(row, text=title, font=font(22, "bold"), fg=colour, bg=BG).pack(side="left", padx=8)
    return row


def card(master, **kw) -> tk.Frame:
    return tk.Frame(master, bg=SURFACE, highlightbackground=LINE, highlightthickness=1, **kw)


def clear(frame: tk.Widget) -> None:
    for child in frame.winfo_children():
        child.destroy()


class Screen(tk.Frame):
    def __init__(self, app: App) -> None:
        super().__init__(app.body, bg=BG, padx=int(24 * app.s), pady=int(16 * app.s))
        self.app, self.s = app, app.s

    def on_show(self) -> None: ...

    def on_hide(self) -> None: ...


# Speak ----------------------------------------------------------------------------------


class SpeakScreen(Screen):
    """Tap the microphone, speak Rohingya, read (or hear) the English."""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        s = self.s
        title_row(self, "mic", "Speak", SPEAK, s).pack(anchor="w")
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, pady=(12 * s, 0))

        left = tk.Frame(body, bg=BG, width=int(300 * s))
        left.pack(side="left", fill="y")
        self.mic = MicButton(left, SPEAK, self.toggle, diameter=170, scale=s)
        self.mic.pack(pady=(10 * s, 0))
        self.hint = text_block(left, "Tap, speak Rohingya, tap again.", 12, MUTED,
                               wrap=int(260 * s))
        self.hint.pack(pady=(0, 14 * s))
        buttons = tk.Frame(left, bg=BG)
        buttons.pack()
        IconButton(buttons, "folder", "Open recording", self.open_file, colour=SPEAK, size=22,
                   filled=False, layout="row", scale=s, font_size=10).pack(pady=4)
        self.demo_button = IconButton(buttons, "play", "Demo recording", self.demo, colour=TEACH,
                                      size=22, filled=False, layout="row", scale=s, font_size=10)

        self.result = card(body, padx=int(24 * s), pady=int(20 * s))
        self.result.pack(side="left", fill="both", expand=True, padx=(24 * s, 0))
        self.recorder = Recorder()
        self.last_audio: Audio | None = None
        self.english, self.english_audio = "", None
        self._empty()

    def show_demo(self) -> None:
        self.demo_button.pack(pady=4)

    def _empty(self) -> None:
        clear(self.result)
        size = 90 * self.s
        c = tk.Canvas(self.result, width=size, height=size, bg=SURFACE, highlightthickness=0)
        icons.draw(c, "speaker", size / 2, size / 2, size * 0.8, shade(SPEAK, 1.7))
        c.pack(pady=(40 * self.s, 10 * self.s))
        text_block(self.result, "The English translation appears here.", 13, MUTED,
                   bg=SURFACE).pack()

    # recording

    def toggle(self) -> None:
        if self.recorder.recording:
            audio = self.recorder.stop()
            self.mic.set_state("idle")
            if audio.duration < MIN_SECONDS:
                self.app.alert("error", "That was too short. Tap the microphone, speak, "
                                        "then tap again to stop.")
                return
            self.translate(audio)
            return
        try:
            self.recorder.start()
        except RuntimeError as e:
            self.app.alert("error", str(e))
            return
        self.mic.set_state("recording")
        self._tick()

    def _tick(self) -> None:
        if self.recorder.recording:
            self.mic.set_level(self.recorder.level, self.recorder.elapsed)
            self.after(50, self._tick)

    def open_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=AUDIO_TYPES)
        if path:
            self.translate(load_wav(path))

    def demo(self) -> None:
        if self.app.demo_files:
            self.translate(load_wav(self.app.demo_files.phrase))

    def on_hide(self) -> None:
        if self.recorder.recording:
            self.recorder.stop()
            self.mic.set_state("idle")

    # translating

    def translate(self, audio: Audio) -> None:
        self.last_audio = audio
        self.mic.set_state("busy")

        def job():
            engine = self.app.engine()
            result = engine.pipeline().run(audio, speak=False)  # text first, voice after
            matches = [m for m in engine.lexicon().lookup(audio) if m.confident]
            return result, matches

        def done(value) -> None:
            self.mic.set_state("idle")
            self.show_result(*value)

        self.app.run("Translating", job, done, on_fail=lambda: self.mic.set_state("idle"))

    def say_english(self) -> None:
        """Read the English aloud: made once per result, then replayed."""
        if self.english_audio is not None:
            play(self.english_audio)
            return
        text = self.english
        self.say_button.set_enabled(False)

        def job():
            return self.app.engine().pipeline().synthesizer.synthesize(text)

        def done(audio: Audio) -> None:
            self.say_button.set_enabled(True)
            if text == self.english:  # still showing the same result
                self.english_audio = audio
                play(audio)

        self.app.run("Reading aloud", job, done,
                     on_fail=lambda: self.say_button.set_enabled(True))

    def show_result(self, result, matches) -> None:
        s = self.s
        clear(self.result)
        self.english, self.english_audio = result.english.text, None
        top = tk.Frame(self.result, bg=SURFACE)
        top.pack(fill="x")
        voice = bool(self.app.config.synthesizer)
        if voice:  # big button: hear the English
            self.say_button = IconButton(top, "speaker", "English", self.say_english,
                                         colour=SPEAK, size=34, scale=s, bg=SURFACE,
                                         font_size=10)
            self.say_button.pack(side="left", anchor="n")
        tk.Label(top, text=result.english.text, font=font(24, "bold"), fg=INK, bg=SURFACE,
                 wraplength=int(460 * s), justify="left", anchor="w").pack(
            side="left", fill="x", expand=True, padx=(16 * s, 0))
        # small button: hear the original Rohingya recording again
        IconButton(top, "mic", "Recording", lambda: self.last_audio and play(self.last_audio),
                   colour=SPEAK, size=20, filled=False, layout="row", scale=s, bg=SURFACE,
                   font_size=9).pack(side="right", anchor="n")

        sure = (result.english.confidence or 0) >= 0.7
        row = tk.Frame(self.result, bg=SURFACE)
        row.pack(anchor="w", pady=(18 * s, 0))
        ConfidenceDots(row, result.english.confidence, s).pack(side="left")
        text = "sure" if sure else "not sure: check with an interpreter"
        tk.Label(row, text=text, font=font(12, "bold"), fg=GOOD if sure else WARN,
                 bg=SURFACE).pack(side="left", padx=10 * s)

        if voice and self.app.config.read_aloud:
            self.say_english()
        if result.transcript:
            text_block(self.result, f"Rohingya text: {result.transcript.text}", 11, MUTED,
                       bg=SURFACE).pack(anchor="w", pady=(10 * s, 0))
        if matches:
            text_block(self.result, "In the dictionary", 11, MUTED, bg=SURFACE,
                       weight="bold").pack(anchor="w", pady=(22 * s, 6 * s))
            chips = tk.Frame(self.result, bg=SURFACE)
            chips.pack(anchor="w")
            for m in matches[:4]:
                self.app.word_chip(chips, m.entry).pack(side="left", padx=(0, 10 * s))


# Words ----------------------------------------------------------------------------------


class WordsScreen(Screen):
    """Every word as a picture card, coloured by how much it is trusted."""

    FILTERS = ("all", "verified", "corroborated", "proposed", "disputed")

    def __init__(self, app: App) -> None:
        super().__init__(app)
        s = self.s
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x")
        title_row(head, "book", "Words", WORDS, s).pack(side="left")
        IconButton(head, "save", "Export", self.export, colour=MUTED, size=22, filled=False,
                   layout="row", scale=s, font_size=10).pack(side="right")
        IconButton(head, "search", "Which word?", self.voice_search, colour=WORDS, size=26,
                   layout="row", scale=s).pack(side="right", padx=10 * s)

        self.filter_row = tk.Frame(self, bg=BG)
        self.filter_row.pack(fill="x", pady=(12 * s, 8 * s))
        self.filter = "all"
        self.filter_buttons: dict[str, IconButton] = {}

        self.scroll = ScrollFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self.entries: list[tuple[Any, list]] = []
        self.cards: dict[int, tk.Frame] = {}
        self._columns = 0
        self.scroll.canvas.bind("<Configure>", self._on_resize, add="+")

    def on_show(self) -> None:
        self.refresh()

    def refresh(self, then=None) -> None:
        def job():
            lex = self.app.engine().lexicon()
            return [(e, lex.store.clips(e.id)) for e in lex.entries()], lex.store.root

        def done(value) -> None:
            self.entries, self.clip_root = value
            self._filters()
            self._layout(force=True)
            if then:
                then()

        self.app.run("Reading the dictionary", job, done)

    def _filters(self) -> None:
        clear(self.filter_row)
        counts = {"all": len(self.entries)}
        for e, _ in self.entries:
            counts[e.status.value] = counts.get(e.status.value, 0) + 1
        for name in self.FILTERS:
            colour, icon, caption = STATUS.get(name, (WORDS, "book", "all"))
            b = IconButton(self.filter_row, icon, f"{caption}  {counts.get(name, 0)}",
                           lambda n=name: self._set_filter(n), colour=colour, size=18,
                           filled=False, layout="row", scale=self.s, font_size=10)
            b.set_selected(name == self.filter)
            b.pack(side="left", padx=(0, 8 * self.s))
            self.filter_buttons[name] = b

    def _set_filter(self, name: str) -> None:
        self.filter = name
        for n, b in self.filter_buttons.items():
            b.set_selected(n == name)
        self._layout(force=True)

    def _on_resize(self, event) -> None:
        self._layout()

    def _layout(self, force: bool = False) -> None:
        card_w = int(180 * self.s)  # 150 px picture + padding and border
        width = self.scroll.canvas.winfo_width()
        columns = max(1, width // (card_w + int(16 * self.s)))
        if columns == self._columns and not force:
            return
        self._columns = columns
        clear(self.scroll.inner)
        self.cards = {}
        shown = [(e, c) for e, c in self.entries
                 if self.filter == "all" or e.status.value == self.filter]
        if not shown:
            empty = text_block(self.scroll.inner, "No words yet. Use Teach to add the first one."
                               if not self.entries else "No words with this colour.", 13)
            empty.grid(row=0, column=0, padx=10, pady=30)
            return
        for i, (entry, clips) in enumerate(shown):
            frame = self._card(entry, clips)
            frame.grid(row=i // columns, column=i % columns, padx=int(8 * self.s),
                       pady=int(8 * self.s), sticky="n")
            self.cards[entry.id] = frame

    def _card(self, entry, clips) -> tk.Frame:
        s = self.s
        colour = STATUS[entry.status.value][0]
        frame = tk.Frame(self.scroll.inner, bg=SURFACE, highlightbackground=colour,
                         highlightthickness=max(2, int(3 * s)), padx=int(12 * s),
                         pady=int(12 * s), cursor="hand2")
        picture = picture_or_icon(frame, self.app.picture_for(entry.meaning), int(150 * s), colour)
        picture.pack()
        tk.Label(frame, text=entry.meaning, font=font(15, "bold"), fg=INK, bg=SURFACE).pack(
            pady=(8 * s, 4 * s))
        StatusBadge(frame, entry.status.value, s, bg=SURFACE).pack()
        sp = entry.support
        AgreementMeter(frame, sp.speakers, self.app.config.lexicon.min_speakers, sp.vision,
                       sp.conflicts, colour, s, bg=SURFACE).pack(pady=(8 * s, 6 * s))
        if clips:
            IconButton(frame, "speaker", "", lambda: self.app.play_clip(clips[0]),
                       colour=colour, size=22, filled=False, scale=s, bg=SURFACE).pack()
        for widget in (frame, picture):
            widget.bind("<Button-1>", lambda _, e=entry, c=clips: self.app.word_details(e, c))
        return frame

    def highlight(self, entry_id: int) -> None:
        if self.filter != "all":
            self._set_filter("all")
        frame = self.cards.get(entry_id)
        if frame is None:
            return
        self.scroll.scroll_to(frame)
        original = frame.cget("highlightbackground")

        def flash(n: int) -> None:
            if frame.winfo_exists():
                frame.configure(highlightbackground=WORDS if n % 2 == 0 else original)
                if n < 5:
                    frame.after(250, flash, n + 1)
        flash(0)

    def voice_search(self) -> None:
        audio = dialogs.record(self.app.root, "Say the word", WORDS, self.s)
        if audio is None:
            return
        if audio.duration < MIN_SECONDS:
            self.app.alert("error", "That was too short. Try again.")
            return

        def done(matches) -> None:
            confident = [m for m in matches if m.confident]
            if confident:
                self.highlight(confident[0].entry.id)
            else:
                self.app.alert("info", "This word is not in the dictionary yet. "
                                       "You can add it with Teach.")

        self.app.run("Looking up", lambda: self.app.engine().lexicon().lookup(audio), done)

    def export(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="lexicon_verified.csv")
        if not path:
            return

        def done(n: int) -> None:
            self.app.alert("done", f"Saved {n} verified recordings to\n{path}")

        self.app.run("Exporting", lambda: self.app.engine().lexicon().export_csv(path), done)


# Teach ----------------------------------------------------------------------------------


class TeachScreen(Screen):
    """Three steps: pick a picture, say the word, save."""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        s = self.s
        title_row(self, "teach", "Teach a word", TEACH, s).pack(anchor="w")
        steps = tk.Frame(self, bg=BG)
        steps.pack(fill="both", expand=True, pady=(12 * s, 0))
        steps.columnconfigure(0, weight=3)
        steps.columnconfigure(1, weight=2)
        steps.columnconfigure(2, weight=2)
        steps.rowconfigure(0, weight=1)

        self.meaning = tk.StringVar()
        self.speaker = tk.StringVar()
        self.consent = tk.StringVar()
        for var in (self.meaning, self.speaker, self.consent):
            var.trace_add("write", lambda *_: self._update_save())
        self.audio: Audio | None = None
        self.photo = None
        self.tiles: dict[str, tk.Frame] = {}

        one = self._step(steps, 0, "1", "picture", "What is it?")
        self.pictures = ScrollFrame(one, bg=SURFACE)
        self.pictures.pack(fill="both", expand=True)
        self.pictures.canvas.bind("<Configure>", self._grid_tiles, add="+")
        row = tk.Frame(one, bg=SURFACE)
        row.pack(fill="x", pady=(8 * s, 0))
        tk.Label(row, text="or type:", font=font(11), fg=MUTED, bg=SURFACE).pack(side="left")
        tk.Entry(row, textvariable=self.meaning, font=font(14), relief="solid", bd=1).pack(
            side="left", fill="x", expand=True, padx=(8 * s, 0))
        self.meaning.trace_add("write", lambda *_: self._mark_tile())

        two = self._step(steps, 1, "2", "mic", "Say it")
        self.mic = MicButton(two, TEACH, self.toggle, diameter=120, scale=s)
        self.mic.pack(pady=(6 * s, 0))
        self.wave = Waveform(two, int(220 * s), int(48 * s), TEACH)
        self.wave.pack(pady=(4 * s, 8 * s))
        self.play_button = IconButton(two, "speaker", "Listen", self.listen, colour=TEACH,
                                      size=22, filled=False, layout="row", scale=s, bg=SURFACE,
                                      font_size=10)
        self.play_button.pack()
        self.play_button.set_enabled(False)
        self.recorder = Recorder()

        three = self._step(steps, 2, "3", "check", "Save")
        for label, var, hint in [("Speaker", self.speaker, "e.g. S014"),
                                 ("Consent", self.consent, "consent record ID")]:
            r = tk.Frame(three, bg=SURFACE)
            r.pack(fill="x", pady=3 * s)
            c = tk.Canvas(r, width=26 * s, height=26 * s, bg=SURFACE, highlightthickness=0)
            icons.draw(c, "person" if label == "Speaker" else "check", 13 * s, 13 * s, 22 * s,
                       MUTED)
            c.pack(side="left")
            tk.Entry(r, textvariable=var, font=font(12), relief="solid", bd=1, width=14).pack(
                side="left", fill="x", expand=True, padx=(6 * s, 0))
            text_block(three, f"{label}: {hint}", 9, MUTED, bg=SURFACE).pack(anchor="w")
        self.photo_button = IconButton(three, "camera", "Add photo", self.add_photo, colour=SEE,
                                       size=22, filled=False, layout="row", scale=s, bg=SURFACE,
                                       font_size=10)
        self.photo_button.pack(pady=(12 * s, 4 * s))
        self.save_button = IconButton(three, "check", "Save", self.save, colour=GOOD, size=44,
                                      scale=s, bg=SURFACE)
        self.save_button.pack(pady=(10 * s, 0))
        self.save_button.set_enabled(False)

        self.outcome = tk.Frame(self, bg=BG)
        self.outcome.pack(fill="x", pady=(12 * s, 0))

    def _step(self, master, column: int, number: str, icon: str, title: str) -> tk.Frame:
        s = self.s
        frame = card(master, padx=int(14 * s), pady=int(12 * s))
        frame.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 12 * s, 0))
        head = tk.Frame(frame, bg=SURFACE)
        head.pack(fill="x", pady=(0, 8 * s))
        size = 34 * s
        c = tk.Canvas(head, width=size, height=size, bg=SURFACE, highlightthickness=0)
        c.create_oval(1, 1, size - 1, size - 1, fill=TEACH, outline="")
        c.create_text(size / 2, size / 2, text=number, fill="white", font=font(14, "bold"))
        c.pack(side="left")
        c2 = tk.Canvas(head, width=size, height=size, bg=SURFACE, highlightthickness=0)
        icons.draw(c2, icon, size / 2, size / 2, size * 0.8, TEACH)
        c2.pack(side="left", padx=(8 * s, 0))
        tk.Label(head, text=title, font=font(15, "bold"), fg=INK, bg=SURFACE).pack(
            side="left", padx=6 * s)
        return frame

    def on_show(self) -> None:
        self.load_pictures()

    def load_pictures(self) -> None:
        clear(self.pictures.inner)
        self.tiles = {}
        prompts = self.app.prompts()
        if not prompts:
            text_block(self.pictures.inner, "Put pictures in the prompts folder, named after "
                       "what they show (for example water.jpg).", 11, MUTED, bg=SURFACE,
                       wrap=int(260 * self.s)).pack(pady=20)
            return
        size = int(86 * self.s)
        for meaning, path in prompts.items():
            tile = tk.Frame(self.pictures.inner, bg=SURFACE, highlightbackground=SURFACE,
                            highlightthickness=max(2, int(3 * self.s)), cursor="hand2",
                            padx=2, pady=2)
            pic = picture_or_icon(tile, path, size, TEACH)
            pic.pack()
            name = tk.Label(tile, text=meaning, font=font(10), fg=INK, bg=SURFACE)
            name.pack()
            for w in (tile, pic, name):
                w.bind("<Button-1>", lambda _, m=meaning: self.meaning.set(m))
            self.tiles[meaning] = tile
        self._grid_tiles()
        self._mark_tile()

    def _grid_tiles(self, event=None) -> None:
        """As many picture columns as fit the step's width."""
        width = self.pictures.canvas.winfo_width()
        columns = max(2, width // int(100 * self.s)) if width > 1 else 3
        for i, tile in enumerate(self.tiles.values()):
            tile.grid(row=i // columns, column=i % columns, padx=3, pady=3)

    def _mark_tile(self) -> None:
        chosen = self.meaning.get().strip().lower()
        for meaning, tile in self.tiles.items():
            tile.configure(highlightbackground=TEACH if meaning == chosen else SURFACE)

    def toggle(self) -> None:
        if self.recorder.recording:
            audio = self.recorder.stop()
            self.mic.set_state("idle")
            if audio.duration < MIN_SECONDS:
                self.app.alert("error", "That was too short. Tap, say the word, tap again.")
                return
            self.set_audio(audio)
            return
        try:
            self.recorder.start()
        except RuntimeError as e:
            self.app.alert("error", str(e))
            return
        self.mic.set_state("recording")
        self._tick()

    def _tick(self) -> None:
        if self.recorder.recording:
            self.mic.set_level(self.recorder.level, self.recorder.elapsed)
            self.after(50, self._tick)

    def set_audio(self, audio: Audio | None) -> None:
        self.audio = audio
        self.wave.show(audio.samples if audio is not None else None)
        self.play_button.set_enabled(audio is not None)
        self._update_save()

    def listen(self) -> None:
        if self.audio is not None:
            play(self.audio)

    def add_photo(self) -> None:
        photo = dialogs.take_photo(self.app.root, self.s, SEE)
        if photo is not None:
            self.photo = photo
            self.photo_button.configure_button(icon="check", text="Photo added")

    def _update_save(self) -> None:
        ready = bool(self.audio is not None and self.meaning.get().strip()
                     and self.speaker.get().strip() and self.consent.get().strip())
        self.save_button.set_enabled(ready)

    def on_hide(self) -> None:
        if self.recorder.recording:
            self.recorder.stop()
            self.mic.set_state("idle")

    def save(self) -> None:
        audio, photo, meaning = self.audio, self.photo, self.meaning.get()
        chosen_picture = meaning.strip().lower() in self.tiles
        args = {"speaker_id": self.speaker.get(), "consent_id": self.consent.get(),
                "source": "prompt" if chosen_picture else "teach"}

        def job():
            lex = self.app.engine().lexicon(vision=photo is not None)
            return lex.teach(audio, meaning, image=photo, **args), lex.vision_is_placeholder

        def done(value) -> None:
            result, placeholder = value
            self.show_outcome(result, placeholder)
            self.set_audio(None)
            self.photo = None
            self.photo_button.configure_button(icon="camera", text="Add photo")
            self.meaning.set("")
            self.app.words.refresh()

        self.app.run("Saving", job, done)

    def show_outcome(self, result, placeholder: bool) -> None:
        s = self.s
        clear(self.outcome)
        e = result.entry
        colour = STATUS[e.status.value][0]
        box = tk.Frame(self.outcome, bg=SURFACE, highlightbackground=colour,
                       highlightthickness=max(2, int(3 * s)), padx=int(14 * s), pady=int(10 * s))
        box.pack(fill="x")
        size = 40 * s
        c = tk.Canvas(box, width=size, height=size, bg=SURFACE, highlightthickness=0)
        icons.draw(c, "check", size / 2, size / 2, size, GOOD)
        c.pack(side="left")
        tk.Label(box, text=e.meaning, font=font(16, "bold"), fg=INK, bg=SURFACE).pack(
            side="left", padx=(10 * s, 12 * s))
        StatusBadge(box, e.status.value, s, bg=SURFACE).pack(side="left")
        sp = e.support
        AgreementMeter(box, sp.speakers, self.app.config.lexicon.min_speakers, sp.vision,
                       sp.conflicts, colour, s, bg=SURFACE).pack(side="left", padx=12 * s)
        notes = []
        if result.vision:
            notes.append("photo agrees" if result.vision.agrees
                         else f"photo looks like: {result.vision.top_label}")
            if placeholder:
                notes.append("(stand-in image model)")
        for other in result.conflicts:
            notes.append(f"sounds like '{other.meaning}': marked unclear")
        if notes:
            text_block(box, "\n".join(notes), 11, WARN if result.conflicts else MUTED,
                       bg=SURFACE).pack(side="left", padx=8 * s)

    def prefill_demo(self) -> None:
        files = self.app.demo_files
        if not files:
            return
        self.meaning.set("house")
        self.speaker.set("DEMO-S02")
        from rohingya_translate.demo import CONSENT

        self.consent.set(CONSENT)
        self.set_audio(load_wav(files.word.with_name("word_house.wav")))


# See ------------------------------------------------------------------------------------


class SeeScreen(Screen):
    """Point the camera at something to get English words for it, then teach the Rohingya."""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        s = self.s
        title_row(self, "camera", "See", SEE, s).pack(anchor="w")
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, pady=(12 * s, 0))

        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="y")
        self.view_w, self.view_h = int(440 * s), int(330 * s)
        self.view = tk.Canvas(left, width=self.view_w, height=self.view_h, bg="#111827",
                              highlightthickness=0, cursor="hand2")
        self.view.pack()
        self.view.bind("<Button-1>", lambda _: self.camera is None and self.start_camera())
        buttons = tk.Frame(left, bg=BG)
        buttons.pack(pady=(12 * s, 0))
        self.shoot = IconButton(buttons, "camera", "Take picture", self.take, colour=SEE, size=30,
                                layout="row", scale=s)
        self.shoot.pack(side="left", padx=4)
        IconButton(buttons, "folder", "Open photo", self.open_file, colour=SEE, size=22,
                   filled=False, layout="row", scale=s, font_size=10).pack(side="left", padx=4)
        self.demo_button = IconButton(buttons, "play", "Demo picture", self.demo, colour=TEACH,
                                      size=22, filled=False, layout="row", scale=s, font_size=10)

        self.results = card(body, padx=int(18 * s), pady=int(14 * s))
        self.results.pack(side="left", fill="both", expand=True, padx=(24 * s, 0))
        self.camera = None
        self.frame = None
        self._idle_view()
        text_block(self.results, "Words for the picture appear here. Tap a word's teach button "
                   "to record its Rohingya name.", 12, MUTED, bg=SURFACE,
                   wrap=int(320 * s)).pack(pady=30 * s)

    def show_demo(self) -> None:
        self.demo_button.pack(side="left", padx=4)

    def _idle_view(self) -> None:
        self.view.delete("all")
        icons.draw(self.view, "camera", self.view_w / 2, self.view_h / 2 - 16 * self.s,
                   90 * self.s, "#374151", )
        self.view.create_text(self.view_w / 2, self.view_h / 2 + 60 * self.s,
                              text="Tap to start the camera", fill="#9CA3AF", font=font(12))

    def start_camera(self) -> None:
        try:
            from rohingya_translate.images import Camera

            self.camera = Camera()
        except (ImportError, RuntimeError) as e:
            self.app.alert("error", str(e))
            return
        self._live()

    def stop_camera(self) -> None:
        if self.camera is not None:
            self.camera.close()
            self.camera = None

    def _live(self) -> None:
        if self.camera is None or not self.winfo_viewable():
            return
        frame = self.camera.read()
        if frame is not None:
            self.frame = frame
            self._show_image(frame)
        self.after(40, self._live)

    def _show_image(self, rgb) -> None:
        from rohingya_translate.images import to_png_base64

        h, w = rgb.shape[:2]
        width = min(self.view_w, int(w * self.view_h / h))
        picture = tk.PhotoImage(data=to_png_base64(rgb, max_width=width))
        self.view.delete("all")
        self.view.create_image(self.view_w / 2, self.view_h / 2, image=picture)
        self.view.image = picture

    def take(self) -> None:
        if self.camera is None:
            self.start_camera()
            return
        frame = self.frame
        self.stop_camera()
        if frame is not None:
            self.look_at(frame)

    def open_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=IMAGE_TYPES)
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path) -> None:
        try:
            from rohingya_translate.images import load_image

            image = load_image(path)
        except (ImportError, ValueError) as e:
            self.app.alert("error", str(e))
            return
        self.stop_camera()
        self.look_at(image)

    def demo(self) -> None:
        files = self.app.demo_files
        if files and files.picture:
            self.open_path(files.picture.with_name("fish.png"))

    def look_at(self, image) -> None:
        self._show_image(image)
        self.shoot.configure_button(text="New picture")

        def job():
            lex = self.app.engine().lexicon(vision=True)
            return lex.suggest(image, limit=6), lex.vision_is_placeholder

        self.app.run("Looking at the picture", job, lambda v: self.show_labels(*v))

    def show_labels(self, labels, placeholder: bool) -> None:
        s = self.s
        clear(self.results)
        if placeholder:
            note = tk.Frame(self.results, bg=SURFACE)
            note.pack(fill="x", pady=(0, 10 * s))
            c = tk.Canvas(note, width=24 * s, height=24 * s, bg=SURFACE, highlightthickness=0)
            icons.draw(c, "warning", 12 * s, 12 * s, 22 * s, WARN)
            c.pack(side="left")
            text_block(note, "Stand-in image model: it does not really see. Choose the "
                             "models settings for real results.", 10, WARN, bg=SURFACE,
                       wrap=int(300 * s)).pack(side="left", padx=6)
        best = labels[0].score if labels else 0
        for label in labels:
            row = tk.Frame(self.results, bg=SURFACE)
            row.pack(fill="x", pady=4 * s)
            picture_or_icon(row, self.app.picture_for(label.text), int(48 * s), SEE).pack(
                side="left")
            mid = tk.Frame(row, bg=SURFACE)
            mid.pack(side="left", fill="x", expand=True, padx=10 * s)
            tk.Label(mid, text=label.text, font=font(14, "bold"), fg=INK, bg=SURFACE,
                     anchor="w").pack(fill="x")
            bar_w, bar_h = int(180 * s), int(10 * s)
            bar = tk.Canvas(mid, width=bar_w, height=bar_h, bg=SURFACE, highlightthickness=0)
            icons.round_rect(bar, 0, 0, bar_w, bar_h, bar_h / 2, fill=LINE, outline="")
            share = label.score / best if best > 0 else 0
            if share > 0:
                icons.round_rect(bar, 0, 0, max(bar_h, bar_w * share), bar_h, bar_h / 2,
                                 fill=SEE, outline="")
            bar.pack(anchor="w", pady=(2, 0))
            IconButton(row, "teach", "", lambda m=label.text: self.app.teach_word(m),
                       colour=TEACH, size=22, filled=False, scale=s, bg=SURFACE).pack(
                side="right")

    def on_hide(self) -> None:
        self.stop_camera()
