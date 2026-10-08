"""The four screens: Speak (translate), Words (dictionary), Teach (add a word) and See (photos).

Kept deliberately simple: one big action per screen, secondary actions as quiet
links, and every word playable. English captions are short and aimed at helpers.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import TYPE_CHECKING

from rohingya_translate.audio import Audio, load_wav
from rohingya_translate.recorder import Recorder, play
from rohingya_translate.ui import dialogs, icons
from rohingya_translate.ui.theme import (
    BG,
    BLUE,
    GOOD,
    INK,
    LINE,
    MUTED,
    RAISED,
    SEE,
    SPEAK,
    STATUS,
    TEACH,
    WARN,
    WORDS,
    font,
    shade,
)
from rohingya_translate.ui.widgets import (
    IconButton,
    MicButton,
    Pill,
    ProgressBar,
    ScrollFrame,
    Segmented,
    StatusBadge,
    ThinScrollbar,
    Waveform,
    entry,
    link,
    load_picture,
    picture_or_icon,
    text_block,
)

if TYPE_CHECKING:
    from rohingya_translate.app import App

AUDIO_TYPES = [("WAV recordings", "*.wav"), ("All files", "*.*")]
IMAGE_TYPES = [("Pictures", "*.jpg *.jpeg *.png *.bmp *.webp"), ("All files", "*.*")]
MIN_SECONDS = 0.3
CAMERA_BG = "#0B1418"


def heading(master, text: str, size: int = 24) -> tk.Label:
    return tk.Label(master, text=text, font=font(size, "heavy"), fg=INK, bg=master.cget("bg"))


def bordered(master, **kw) -> tk.Frame:
    """A Duolingo-style card: background colour with a soft border."""
    return tk.Frame(master, bg=BG, highlightbackground=LINE, highlightthickness=2, **kw)


def clear(frame: tk.Widget) -> None:
    for child in frame.winfo_children():
        child.destroy()


class Screen(tk.Frame):
    def __init__(self, app: App) -> None:
        super().__init__(app.body, bg=BG, padx=int(36 * app.s), pady=int(28 * app.s))
        self.app, self.s = app, app.s

    def on_show(self) -> None: ...

    def on_hide(self) -> None: ...


class Recording:
    """Shared press-to-talk logic for a MicButton."""

    def __init__(self, screen: Screen, mic: MicButton, on_audio) -> None:
        self.screen, self.mic, self.on_audio = screen, mic, on_audio
        self.recorder = Recorder()

    def toggle(self) -> None:
        if self.recorder.recording:
            audio = self.recorder.stop()
            self.mic.set_state("idle")
            if audio.duration < MIN_SECONDS:
                self.screen.app.alert("error", "Too short. Tap, speak, then tap again.")
                return
            self.on_audio(audio)
            return
        try:
            self.recorder.start()
        except RuntimeError as e:
            self.screen.app.alert("error", str(e))
            return
        self.mic.set_state("recording")
        self._tick()

    def _tick(self) -> None:
        if self.recorder.recording:
            self.mic.set_level(self.recorder.level, self.recorder.elapsed)
            self.screen.after(50, self._tick)

    def stop(self) -> None:
        if self.recorder.recording:
            self.recorder.stop()
            self.mic.set_state("idle")


# Speak ----------------------------------------------------------------------------------


class SpeakScreen(Screen):
    """Tap the microphone, speak Rohingya, read and hear the English."""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        s = self.s
        heading(self, "Tap and speak Rohingya").pack(pady=(10 * s, 6 * s))
        self.mic = MicButton(self, SPEAK, lambda: self.recording.toggle(), diameter=150, scale=s)
        self.mic.pack()
        self.recording = Recording(self, self.mic, self.translate)
        links = tk.Frame(self, bg=BG)
        links.pack(pady=(0, 18 * s))
        link(links, "or open a recording", self.open_file, colour=MUTED).pack(side="left")
        self.demo_link = link(links, "play a demo phrase", self.demo, colour=TEACH)
        self.result = tk.Frame(self, bg=BG)
        self.result.pack(fill="x", padx=int(40 * s))
        self.last_audio: Audio | None = None
        self.english, self.english_audio = "", None
        self.say_button: IconButton | None = None

    def show_demo(self) -> None:
        self.demo_link.pack(side="left", padx=(24 * self.s, 0))

    def open_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=AUDIO_TYPES)
        if path:
            self.translate(load_wav(path))

    def demo(self) -> None:
        """Each tap translates the next demo phrase."""
        files = self.app.demo_files
        if files and files.phrases:
            self._demo_next = getattr(self, "_demo_next", 0)
            self.translate(load_wav(files.phrases[self._demo_next % len(files.phrases)]))
            self._demo_next += 1

    def on_hide(self) -> None:
        self.recording.stop()

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
        text, button = self.english, self.say_button
        button.set_enabled(False)

        def job():
            return self.app.engine().pipeline().synthesizer.synthesize(text)

        def done(audio: Audio) -> None:
            button.set_enabled(True)
            if text == self.english:  # still showing the same result
                self.english_audio = audio
                play(audio)

        self.app.run("Reading aloud", job, done, on_fail=lambda: button.set_enabled(True))

    def show_result(self, result, matches) -> None:
        s = self.s
        clear(self.result)
        self.english, self.english_audio = result.english.text, None
        box = bordered(self.result, padx=int(22 * s), pady=int(18 * s))
        box.pack(fill="x")
        row = tk.Frame(box, bg=BG)
        row.pack(fill="x")
        voice = bool(self.app.config.synthesizer)
        if voice:
            self.say_button = IconButton(row, "speaker", "", self.say_english, colour=BLUE,
                                         size=30, scale=s)
            self.say_button.pack(side="left", anchor="n")
        tk.Label(row, text=result.english.text, font=font(22, "bold"), fg=INK, bg=BG,
                 wraplength=int(560 * s), justify="left", anchor="w").pack(
            side="left", fill="x", expand=True, padx=(16 * s, 0))

        sure = (result.english.confidence or 0) >= 0.7
        info = tk.Frame(box, bg=BG)
        info.pack(fill="x", pady=(14 * s, 0))
        caption = "sure" if sure else "not sure: ask an interpreter"
        Pill(info, "check" if sure else "warning", caption, GOOD if sure else WARN, s).pack(
            side="left")
        link(info, "replay recording", lambda: self.last_audio and play(self.last_audio),
             colour=MUTED, size=10).pack(side="right")

        if matches:
            text_block(self.result, "IN YOUR DICTIONARY", 10, MUTED, weight="heavy").pack(
                anchor="w", pady=(18 * s, 6 * s))
            chips = tk.Frame(self.result, bg=BG)
            chips.pack(anchor="w")
            for m in matches[:4]:
                self.app.word_chip(chips, m.entry).pack(side="left", padx=(0, 10 * s))
        if voice and self.app.config.read_aloud:
            self.say_english()


# Words ----------------------------------------------------------------------------------


class WordsScreen(Screen):
    """Every word, as picture cards or a sortable table."""

    FILTERS = ("all", "verified", "corroborated", "proposed", "disputed")
    COLUMNS = (("word", "WORD", 180), ("status", "STATUS", 120), ("speakers", "SPEAKERS", 100),
               ("photo", "PHOTO CHECK", 120), ("disagree", "DISAGREE", 100),
               ("spelling", "SPELLING", 140))

    def __init__(self, app: App) -> None:
        super().__init__(app)
        s = self.s
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x")
        heading(top, "Words").pack(side="left")
        self.view = "cards"
        self.toggle = Segmented(top, [("cards", "grid", "Cards"), ("table", "list", "Table")],
                                self.set_view, s)
        self.toggle.select("cards")
        self.toggle.pack(side="right")

        tools = tk.Frame(self, bg=BG)
        tools.pack(fill="x", pady=(16 * s, 10 * s))
        self.query = tk.StringVar()
        self.query.trace_add("write", lambda *_: self._render())
        box = tk.Frame(tools, bg=RAISED, highlightthickness=2, highlightbackground=LINE)
        box.pack(side="left")
        glass = tk.Canvas(box, width=34 * s, height=34 * s, bg=RAISED, highlightthickness=0)
        icons.draw(glass, "search", 18 * s, 17 * s, 20 * s, MUTED)
        glass.pack(side="left", padx=(4 * s, 0))
        search = entry(box, self.query, 13, width=20, accent=WORDS)
        search.configure(highlightthickness=0)
        search.pack(side="left", ipady=int(5 * s), padx=(0, 8 * s))
        IconButton(tools, "mic", "", self.voice_search, colour=WORDS, size=20, filled=False,
                   scale=s).pack(side="left", padx=(8 * s, 0))
        self.filter_row = tk.Frame(tools, bg=BG)
        self.filter_row.pack(side="right")
        self.filter = "all"
        self.filter_buttons: dict[str, IconButton] = {}

        self.content = tk.Frame(self, bg=BG)
        self.content.pack(fill="both", expand=True)
        self.scroll = ScrollFrame(self.content)
        self.scroll.canvas.bind("<Configure>", lambda _: self._render(only_if_resized=True),
                                add="+")
        self.table_frame = tk.Frame(self.content, bg=BG)
        self._build_table()
        self.scroll.pack(fill="both", expand=True)

        self.entries: list = []
        self.clip_root = ""
        self.cards: dict[int, tk.Frame] = {}
        self._columns = 0
        self._sort = ("word", False)

    # data

    def on_show(self) -> None:
        self.refresh()

    def refresh(self, then=None) -> None:
        def job():
            lex = self.app.engine().lexicon()
            return [(e, lex.store.clips(e.id)) for e in lex.entries()], lex.store.root

        def done(value) -> None:
            self.entries, self.clip_root = value
            self._filters()
            self._render()
            if then:
                then()

        self.app.run("Reading the dictionary", job, done)

    def _shown(self) -> list:
        q = self.query.get().strip().lower()
        return [(e, c) for e, c in self.entries
                if (self.filter == "all" or e.status.value == self.filter)
                and (not q or q in e.meaning or q in e.rohingyalish.lower())]

    def _filters(self) -> None:
        clear(self.filter_row)
        counts = {"all": len(self.entries)}
        for e, _ in self.entries:
            counts[e.status.value] = counts.get(e.status.value, 0) + 1
        for name in self.FILTERS:
            colour, _, caption = STATUS.get(name, (BLUE, "", "All"))
            b = IconButton(self.filter_row, "", f"{caption} {counts.get(name, 0)}",
                           lambda n=name: self._set_filter(n), colour=colour, size=14,
                           filled=False, layout="row", scale=self.s, font_size=10, upper=True)
            b.set_selected(name == self.filter)
            b.pack(side="left", padx=(6 * self.s, 0))
            self.filter_buttons[name] = b

    def _set_filter(self, name: str) -> None:
        self.filter = name
        for n, b in self.filter_buttons.items():
            b.set_selected(n == name)
        self._render()

    def set_view(self, view: str) -> None:
        self.view = view
        self.toggle.select(view)
        if view == "table":
            self.scroll.pack_forget()
            self.table_frame.pack(fill="both", expand=True)
        else:
            self.table_frame.pack_forget()
            self.scroll.pack(fill="both", expand=True)
        self._render()

    def _render(self, only_if_resized: bool = False) -> None:
        if self.view == "table":
            if not only_if_resized:
                self._fill_table()
            return
        card_w = int(170 * self.s)
        columns = max(1, self.scroll.canvas.winfo_width() // card_w)
        if only_if_resized and columns == self._columns:
            return
        self._columns = columns
        clear(self.scroll.inner)
        self.cards = {}
        shown = self._shown()
        if not shown:
            text_block(self.scroll.inner, "No words here yet." if self.entries
                       else "No words yet. Add the first one with Teach.", 14).grid(
                row=0, column=0, padx=10, pady=40)
            return
        for i, (word, clips) in enumerate(shown):
            card = self._card(word, clips)
            card.grid(row=i // columns, column=i % columns, padx=int(6 * self.s),
                      pady=int(6 * self.s), sticky="n")
            self.cards[word.id] = card

    # cards

    def _card(self, entry, clips) -> tk.Frame:
        s = self.s
        frame = tk.Frame(self.scroll.inner, bg=BG, highlightbackground=LINE,
                         highlightthickness=2, padx=int(12 * s), pady=int(12 * s), cursor="hand2")
        picture = picture_or_icon(frame, self.app.picture_for(entry.meaning), int(124 * s),
                                  WORDS, bg=BG)
        picture.pack()
        name = tk.Label(frame, text=entry.meaning, font=font(14, "heavy"), fg=INK, bg=BG)
        name.pack(pady=(8 * s, 4 * s))
        row = tk.Frame(frame, bg=BG)
        row.pack(fill="x")
        StatusBadge(row, entry.status.value, s, bg=BG).pack(side="left")
        if clips:
            IconButton(row, "speaker", "", lambda: self.app.play_clip(clips[0]), colour=BLUE,
                       size=16, scale=s, bg=BG).pack(side="right")
        for widget in (frame, picture, name):
            widget.bind("<Button-1>", lambda _, e=entry, c=clips: self.app.word_details(e, c))
        return frame

    # table

    def _build_table(self) -> None:
        s = self.s
        style = ttk.Style(self)
        style.theme_use("clam")  # the only built-in theme whose colours can all be changed
        style.configure("Words.Treeview", background=BG, fieldbackground=BG, foreground=INK,
                        rowheight=int(40 * s), borderwidth=0, font=font(12))
        style.configure("Words.Treeview.Heading", background=BG, foreground=MUTED,
                        font=font(10, "heavy"), relief="flat", borderwidth=0, padding=8)
        style.map("Words.Treeview.Heading", background=[("active", RAISED)])
        style.map("Words.Treeview", background=[("selected", shade(BLUE, 1.75))],
                  foreground=[("selected", INK)])
        style.layout("Words.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        self.table = ttk.Treeview(self.table_frame, style="Words.Treeview",
                                  columns=[c for c, _, _ in self.COLUMNS], show="tree headings")
        self.table.column("#0", width=int(52 * s), stretch=False)  # little pictures
        for key, title, width in self.COLUMNS:
            self.table.heading(key, text=title, anchor="w", command=lambda k=key: self._sort_by(k))
            self.table.column(key, width=int(width * s), anchor="w")
        for status, (colour, _, _) in STATUS.items():
            self.table.tag_configure(status, foreground=colour)
        bar = ThinScrollbar(self.table_frame, self.table.yview, bg=BG)
        self.table.configure(yscrollcommand=bar.set)
        self.table.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.table.bind("<Double-1>", lambda _: self._open_selected())
        self.table.bind("<Return>", lambda _: self._open_selected())
        self.table.bind("<space>", lambda _: self._play_selected())
        self._thumbs: list[tk.PhotoImage] = []

    def _row(self, entry) -> tuple:
        sp = entry.support
        return (entry.meaning, STATUS[entry.status.value][2], f"{sp.speakers}",
                "yes" if sp.vision else "", sp.conflicts or "", entry.rohingyalish)

    def _fill_table(self) -> None:
        self.table.delete(*self.table.get_children())
        self._thumbs = []
        key, reverse = self._sort
        index = [c for c, _, _ in self.COLUMNS].index(key)
        rows = sorted(self._shown(), key=lambda ec: str(self._row(ec[0])[index]).zfill(3),
                      reverse=reverse)
        for e, _ in rows:
            thumb = load_picture(self.app.picture_for(e.meaning), int(30 * self.s)) \
                if self.app.picture_for(e.meaning) else None
            if thumb is not None:
                self._thumbs.append(thumb)
            self.table.insert("", "end", iid=str(e.id), values=self._row(e),
                              image=thumb or "", tags=(e.status.value,))
        for k, title, _ in self.COLUMNS:
            arrow = (" ▼" if reverse else " ▲") if k == key else ""
            self.table.heading(k, text=title + arrow)

    def _sort_by(self, key: str) -> None:
        current, reverse = self._sort
        self._sort = (key, not reverse if key == current else False)
        self._fill_table()

    def _selected(self):
        chosen = self.table.selection()
        if not chosen:
            return None
        return next(((e, c) for e, c in self.entries if str(e.id) == chosen[0]), None)

    def _open_selected(self) -> None:
        found = self._selected()
        if found:
            self.app.word_details(*found)

    def _play_selected(self) -> None:
        found = self._selected()
        if found and found[1]:
            self.app.play_clip(found[1][0])

    # finding a word

    def highlight(self, entry_id: int) -> None:
        self.query.set("")
        if self.filter != "all":
            self._set_filter("all")
        if self.view == "table":
            self.table.selection_set(str(entry_id))
            self.table.see(str(entry_id))
            return
        frame = self.cards.get(entry_id)
        if frame is None:
            return
        self.scroll.scroll_to(frame)

        def flash(n: int) -> None:
            if frame.winfo_exists():
                frame.configure(highlightbackground=BLUE if n % 2 == 0 else LINE)
                if n < 5:
                    frame.after(250, flash, n + 1)
        flash(0)

    def voice_search(self) -> None:
        audio = dialogs.record(self.app.root, "Say the word", WORDS, self.s)
        if audio is None:
            return
        if audio.duration < MIN_SECONDS:
            self.app.alert("error", "Too short. Try again.")
            return

        def done(matches) -> None:
            confident = [m for m in matches if m.confident]
            if confident:
                self.highlight(confident[0].entry.id)
            else:
                self.app.alert("info", "That word is not in the dictionary yet. "
                                       "Add it with Teach.")

        self.app.run("Looking up", lambda: self.app.engine().lexicon().lookup(audio), done)


# Teach ----------------------------------------------------------------------------------


class TeachScreen(Screen):
    """A three-step lesson: pick a picture, say the word, save."""

    TITLES = ("What is it?", "Say it in Rohingya", "Who is speaking?")

    def __init__(self, app: App) -> None:
        super().__init__(app)
        s = self.s
        self.progress = ProgressBar(self, int(600 * s), TEACH, s)
        self.progress.pack(fill="x", pady=(4 * s, 22 * s))
        self.heading = heading(self, "")
        self.heading.pack(anchor="w")
        self.body = tk.Frame(self, bg=BG)
        self.body.pack(fill="both", expand=True, pady=(16 * s, 0))

        self.footer = tk.Frame(self, bg=BG, pady=int(16 * s))
        self.footer.pack(fill="x", side="bottom")
        tk.Frame(self, bg=LINE, height=2).pack(fill="x", side="bottom")

        self.meaning = tk.StringVar()
        self.speaker = tk.StringVar()
        self.consent = tk.StringVar()
        for var in (self.meaning, self.speaker, self.consent):
            var.trace_add("write", lambda *_: self._update_button())
        self.audio: Audio | None = None
        self.photo = None
        self.step = 0
        self.tiles: dict[str, tk.Frame] = {}
        self.main_button: IconButton | None = None
        self.mic: MicButton | None = None
        self.recording: Recording | None = None

    def on_show(self) -> None:
        self.go(self.step)

    def load_pictures(self) -> None:
        if self.step == 0 and self.winfo_ismapped():
            self.go(0)

    def start(self, meaning: str = "") -> None:
        """Begin a new word, keeping the speaker and consent for the next one."""
        self.meaning.set(meaning)
        self.audio, self.photo = None, None
        self.go(0)

    def go(self, step: int) -> None:
        if self.recording:
            self.recording.stop()
        self.step = step
        self.progress.set(step / 3)
        self.heading.configure(text=self.TITLES[step])
        clear(self.body)
        [self._step_picture, self._step_voice, self._step_speaker][step]()
        self._footer()

    # steps

    def _step_picture(self) -> None:
        s = self.s
        grid = ScrollFrame(self.body)
        grid.pack(fill="both", expand=True)
        self.tiles = {}
        prompts = self.app.prompts()
        if not prompts:
            text_block(grid.inner, "Put pictures in the prompts folder, named after what they "
                       "show (for example water.jpg). Or type the word below.", 13).pack(pady=20)
        size = int(96 * s)
        columns = max(3, int(self.app.root.winfo_width() - 330 * s) // int(126 * s))
        for i, (meaning, path) in enumerate(prompts.items()):
            tile = tk.Frame(grid.inner, bg=BG, highlightbackground=LINE, highlightthickness=2,
                            cursor="hand2", padx=6, pady=6)
            pic = picture_or_icon(tile, path, size, TEACH, bg=BG)
            pic.pack()
            name = tk.Label(tile, text=meaning, font=font(11, "bold"), fg=INK, bg=BG)
            name.pack()
            for w in (tile, pic, name):
                w.bind("<Button-1>", lambda _, m=meaning: self.meaning.set(m))
            tile.grid(row=i // columns, column=i % columns, padx=5, pady=5)
            self.tiles[meaning] = tile
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x", pady=(12 * s, 0))
        text_block(row, "or type a word", 11, MUTED, weight="heavy").pack(side="left")
        box = entry(row, self.meaning, 14, accent=TEACH)
        box.pack(side="left", fill="x", expand=True, padx=(12 * s, 0), ipady=int(5 * s))
        self._mark_tile()

    def _mark_tile(self) -> None:
        chosen = self.meaning.get().strip().lower()
        for meaning, tile in self.tiles.items():
            on = meaning == chosen
            colour = BLUE if on else LINE
            tile.configure(highlightbackground=colour, bg=shade(BLUE, 1.85) if on else BG)
            for child in tile.winfo_children():
                child.configure(bg=shade(BLUE, 1.85) if on else BG)

    def _step_voice(self) -> None:
        s = self.s
        word = tk.Frame(self.body, bg=BG)
        word.pack(pady=(0, 6 * s))
        meaning = self.meaning.get().strip().lower()
        picture_or_icon(word, self.app.picture_for(meaning), int(64 * s), TEACH, bg=BG).pack(
            side="left")
        tk.Label(word, text=meaning, font=font(20, "heavy"), fg=INK, bg=BG).pack(
            side="left", padx=12 * s)
        self.mic = MicButton(self.body, TEACH, lambda: self.recording.toggle(), diameter=130,
                             scale=s)
        self.mic.pack()
        self.recording = Recording(self, self.mic, self._set_audio)
        self.wave = Waveform(self.body, int(300 * s), int(52 * s), TEACH)
        self.wave.pack()
        self.wave.show(self.audio.samples if self.audio is not None else None)
        self.listen = link(self.body, "listen", lambda: self.audio is not None and play(self.audio),
                           colour=BLUE)
        self.listen.pack(pady=(10 * s, 0))

    def _set_audio(self, audio: Audio) -> None:
        self.audio = audio
        self.wave.show(audio.samples)
        self._update_button()

    def _step_speaker(self) -> None:
        s = self.s
        form = tk.Frame(self.body, bg=BG)
        form.pack(anchor="w", fill="x")
        for label, var, hint in [("SPEAKER ID", self.speaker, "a code like S014, never a name"),
                                 ("CONSENT ID", self.consent, "the speaker's consent record")]:
            text_block(form, label, 10, MUTED, weight="heavy").pack(anchor="w", pady=(10 * s, 4))
            entry(form, var, 14, width=30, accent=TEACH).pack(anchor="w", ipady=int(6 * s))
            text_block(form, hint, 10, MUTED).pack(anchor="w", pady=(4, 0))
        self.photo_button = IconButton(form, "camera", "Photo added" if self.photo is not None
                                       else "Add a photo (optional)", self._add_photo,
                                       colour=SEE, size=20, filled=False, layout="row", scale=s,
                                       font_size=10, upper=True)
        self.photo_button.pack(anchor="w", pady=(22 * s, 0))

    def _add_photo(self) -> None:
        photo = dialogs.take_photo(self.app.root, self.s, SEE)
        if photo is not None:
            self.photo = photo
            self.photo_button.configure_button(text="PHOTO ADDED")

    # footer and saving

    def _footer(self, outcome=None) -> None:
        s = self.s
        clear(self.footer)
        self.footer.configure(bg=BG)
        if outcome is not None:
            self._outcome(*outcome)
            return
        if self.step > 0:
            link(self.footer, "back", lambda: self.go(self.step - 1), colour=MUTED).pack(
                side="left")
        last = self.step == 2
        self.main_button = IconButton(self.footer, "", "Save" if last else "Continue",
                                      self.save if last else lambda: self.go(self.step + 1),
                                      colour=TEACH, size=20, layout="row", scale=s,
                                      font_size=13, upper=True, min_width=180)
        self.main_button.pack(side="right")
        self._update_button()

    def _update_button(self) -> None:
        if self.step == 0:
            self._mark_tile()
        if self.main_button is None or not self.main_button.winfo_exists():
            return
        ready = [bool(self.meaning.get().strip()), self.audio is not None,
                 bool(self.speaker.get().strip() and self.consent.get().strip())][self.step]
        self.main_button.set_enabled(ready)

    def save(self) -> None:
        audio, photo, meaning = self.audio, self.photo, self.meaning.get()
        args = {"speaker_id": self.speaker.get(), "consent_id": self.consent.get(),
                "source": "prompt" if meaning.strip().lower() in self.app.prompts() else "teach"}

        def job():
            lex = self.app.engine().lexicon(vision=photo is not None)
            return lex.teach(audio, meaning, image=photo, **args), lex.vision_is_placeholder

        def done(value) -> None:
            self.progress.set(1.0)
            self._footer(outcome=value)
            self.app.words.refresh()

        self.app.run("Saving", job, done)

    def _outcome(self, result, placeholder: bool) -> None:
        """A Duolingo-style banner: what was saved and how trusted it is now."""
        s = self.s
        tint = shade(GOOD, 1.85)
        self.footer.configure(bg=tint)
        size = 52 * s
        c = tk.Canvas(self.footer, width=size, height=size, bg=tint, highlightthickness=0)
        c.create_oval(2, 2, size - 2, size - 2, fill=GOOD, outline="")
        icons.draw(c, "check", size / 2, size / 2, size * 0.6, BG)
        c.pack(side="left", padx=(16 * s, 12 * s))
        text = tk.Frame(self.footer, bg=tint)
        text.pack(side="left")
        tk.Label(text, text=f"Saved: {result.entry.meaning}", font=font(16, "heavy"), fg=GOOD,
                 bg=tint).pack(anchor="w")
        notes = []
        if result.vision:
            notes.append("photo agrees" if result.vision.agrees
                         else f"photo looks like {result.vision.top_label}")
        for other in result.conflicts:
            notes.append(f"sounds like '{other.meaning}': marked unclear")
        if notes:
            tk.Label(text, text=" · ".join(notes), font=font(10), fg=INK, bg=tint).pack(anchor="w")
        StatusBadge(self.footer, result.entry.status.value, s, bg=tint).pack(
            side="left", padx=14 * s)
        IconButton(self.footer, "", "Teach another", lambda: self.start(), colour=GOOD,
                   size=20, layout="row", scale=s, font_size=13, upper=True, bg=tint,
                   min_width=200).pack(side="right", padx=(0, 16 * s))
        self.audio, self.photo = None, None

    def prefill_demo(self) -> None:
        files = self.app.demo_files
        if not files:
            return
        from rohingya_translate.demo import CONSENT, NEW_SPEAKER

        self.meaning.set("house")
        self.speaker.set(NEW_SPEAKER)
        self.consent.set(CONSENT)
        self.audio = load_wav(files.word.with_name("word_house.wav"))
        self._mark_tile()

    def on_hide(self) -> None:
        if self.recording:
            self.recording.stop()


# See ------------------------------------------------------------------------------------


class SeeScreen(Screen):
    """Point the camera at something to get English words for it, then teach the Rohingya."""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        s = self.s
        heading(self, "Show me something").pack(anchor="w")
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, pady=(18 * s, 0))

        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="y")
        self.view_w, self.view_h = int(420 * s), int(315 * s)
        self.view = tk.Canvas(left, width=self.view_w, height=self.view_h, bg=CAMERA_BG,
                              highlightthickness=2, highlightbackground=LINE, cursor="hand2")
        self.view.pack()
        self.view.bind("<Button-1>", lambda _: self.camera is None and self.start_camera())
        self.shoot = IconButton(left, "camera", "Take picture", self.take, colour=SEE, size=24,
                                layout="row", scale=s, font_size=13, upper=True,
                                min_width=420)
        self.shoot.pack(pady=(16 * s, 8 * s))
        links = tk.Frame(left, bg=BG)
        links.pack()
        link(links, "or open a photo", self.open_file, colour=MUTED).pack(side="left")
        self.demo_link = link(links, "show a demo picture", self.demo, colour=TEACH)

        self.results = tk.Frame(body, bg=BG)
        self.results.pack(side="left", fill="both", expand=True, padx=(32 * s, 0))
        self.camera = None
        self.frame = None
        self._idle_view()
        text_block(self.results, "Take a picture, and the words for it appear here. "
                   "Tap TEACH to record a word's Rohingya name.", 13, MUTED,
                   wrap=int(320 * s)).pack(anchor="w")

    def show_demo(self) -> None:
        self.demo_link.pack(side="left", padx=(24 * self.s, 0))

    def _idle_view(self) -> None:
        self.view.delete("all")
        icons.draw(self.view, "camera", self.view_w / 2, self.view_h / 2 - 16 * self.s,
                   80 * self.s, LINE)
        self.view.create_text(self.view_w / 2, self.view_h / 2 + 52 * self.s,
                              text="TAP TO START THE CAMERA", fill=MUTED, font=font(11, "heavy"))

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
            pictures = sorted(files.picture.parent.glob("*.png"))
            self._demo_next = getattr(self, "_demo_next", 0)
            self.open_path(pictures[self._demo_next % len(pictures)])
            self._demo_next += 7  # jump around the library

    def look_at(self, image) -> None:
        self._show_image(image)
        self.shoot.configure_button(text="NEW PICTURE")

        def job():
            lex = self.app.engine().lexicon(vision=True)
            return lex.suggest(image, limit=5), lex.vision_is_placeholder

        self.app.run("Looking at the picture", job, lambda v: self.show_labels(*v))

    def show_labels(self, labels, placeholder: bool) -> None:
        s = self.s
        clear(self.results)
        tk.Label(self.results, text="I SEE", font=font(11, "heavy"), fg=MUTED, bg=BG).pack(
            anchor="w", pady=(0, 8 * s))
        best = labels[0].score if labels else 0
        for label in labels:
            row = tk.Frame(self.results, bg=BG, highlightbackground=LINE, highlightthickness=2,
                           padx=int(10 * s), pady=int(8 * s))
            row.pack(fill="x", pady=4 * s)
            picture_or_icon(row, self.app.picture_for(label.text), int(46 * s), SEE, bg=BG).pack(
                side="left")
            mid = tk.Frame(row, bg=BG)
            mid.pack(side="left", fill="x", expand=True, padx=12 * s)
            tk.Label(mid, text=label.text, font=font(14, "heavy"), fg=INK, bg=BG,
                     anchor="w").pack(fill="x")
            bar = ProgressBar(mid, int(170 * s), SEE, s, height=10)
            bar.set(label.score / best if best > 0 else 0)
            bar.pack(anchor="w", pady=(4, 0))
            IconButton(row, "", "Teach", lambda m=label.text: self.app.teach_word(m),
                       colour=TEACH, size=14, filled=False, layout="row", scale=s,
                       font_size=10, upper=True).pack(side="right")
        if placeholder:
            text_block(self.results, "Stand-in image model: it doesn't really see. Choose the "
                       "models settings for real results.", 10, MUTED, wrap=int(360 * s)).pack(
                anchor="w", pady=(10 * s, 0))

    def on_hide(self) -> None:
        self.stop_camera()
