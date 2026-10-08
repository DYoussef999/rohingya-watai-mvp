# Getting started

This guide walks you through setting up Rohingya Translate on a Windows computer and running it for the first time. You don't need any programming experience. Every command is given in full, and you can copy and paste it.

It takes about 15 minutes.

> **Heads-up:** the project is still early. Out of the box it runs with a placeholder model that only reports how long your recording is. That's on purpose: it lets you check that everything is set up correctly. Step 8 shows how to switch on a real speech model.

## The short way

1. Install Python (Step 1 below).
2. Open the `rohingya-translate` folder and **double-click `run.bat`**.

The first time, a black window appears and spends a few minutes setting things up. Then the app window opens. After that, double-clicking `run.bat` opens the app straight away. Keep the black window open while you use the app; it shows progress and any error messages.

To look around with example data already filled in, double-click **`demo.bat`** instead. It opens the same app (with "demo data" in the title bar), pre-filled with made-up data: about 45 words with picture cards, 15 phrases (tap **Demo recording** repeatedly to go through them), and dictionary entries in every status. Each tab has a hint telling you what to click. The demo is rebuilt fresh every time and kept separate from the real dictionary. Its "recordings" are tone patterns, not speech, so the demo can only recognise its own files.

If that works, skip ahead to [Using the app](#using-the-app). The steps below do the same setup by hand, which helps when something goes wrong or when you want to use the command line.

---

## What you'll need

- A Windows 10 or 11 computer
- An internet connection (for the setup only; the app itself runs offline)
- The project folder (`rohingya-translate`) somewhere on your computer, for example in `Documents`

---

## Step 1: Install Python

Python is the programming language the app is written in. You need **version 3.11 or 3.12**. Newer versions may not work yet with the speech libraries.

1. Go to <https://www.python.org/downloads/windows/>.
2. Find the latest **Python 3.11** release (or 3.12) and download the **Windows installer (64-bit)**.
3. Run the installer. On the first screen, **tick "Add python.exe to PATH"** at the bottom, then click **Install Now**.

To check it worked, go on to Step 2 and run:

```powershell
py -3.11 --version
```

You should see something like `Python 3.11.9`. If you installed 3.12, use `py -3.12` in place of `py -3.11` everywhere in this guide.

---

## Step 2: Open a terminal in the project folder

A terminal is a window where you type commands. Windows comes with one called **PowerShell**.

1. Open File Explorer and go into the `rohingya-translate` folder. You should see files like `README.md` and `pyproject.toml`.
2. Click an empty space in the folder, hold **Shift**, right-click, and choose **Open in Terminal** (or **Open PowerShell window here**).

A window opens with a line ending in something like:

```
PS C:\Users\you\Documents\rohingya-translate>
```

This is the **prompt**. It shows which folder you're in. Every command below is typed here, followed by **Enter**.

> If you use Visual Studio Code: open the folder there and choose **Terminal → New Terminal** from the menu. That gives you the same thing.

---

## Step 3: Create a virtual environment

A **virtual environment** (often called a "venv") is a private folder of Python libraries just for this project. It keeps the project's libraries separate from everything else on your computer, so nothing clashes.

Create one with:

```powershell
py -3.11 -m venv .venv
```

This makes a new folder called `.venv` inside the project. You only do this **once**.

---

## Step 4: Activate the virtual environment

"Activating" tells this terminal window to use the project's private Python instead of the system one.

```powershell
.venv\Scripts\Activate.ps1
```

When it works, `(.venv)` appears at the start of the prompt:

```
(.venv) PS C:\Users\you\Documents\rohingya-translate>
```

You need to activate it **each time you open a new terminal window**. When you're done, you can type `deactivate` to switch it off, or just close the window.

### If you see an error about "running scripts is disabled"

Windows blocks scripts like this one by default. Allow them for your user account (you only need to do this once):

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Type `Y` and press Enter if it asks, then run the activate command again.

---

## Step 5: Install the project

With the venv active (you can see `(.venv)` on the prompt), run:

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The first line updates `pip`, Python's installer. The second installs the app and the tools used for testing. It prints a lot of text and should end with a line starting `Successfully installed`.

You only need to do this once (or again if the project's list of libraries changes).

---

## Step 6: Check everything works

Run the automatic tests:

```powershell
python -m pytest
```

You should see a row of dots and a line like:

```
9 passed in 0.22s
```

If you see `passed` and no `failed`, your setup is working.

---

## Step 7: Translate a recording

The app reads **WAV** audio files. Run it on a recording like this:

```powershell
rtranslate path\to\recording.wav
```

Replace `path\to\recording.wav` with the location of your file. Tip: you can drag the file from File Explorer into the terminal window to paste its full path.

With the placeholder model, you'll see something like:

```
English:  <2.0s of audio>
```

That means the app read your file and ran the whole pipeline. To see the full result, including timestamps, add `--json`:

```powershell
rtranslate path\to\recording.wav --json
```

### Converting phone recordings to WAV

Phones usually save audio as `.m4a` or `.mp3`. Convert it with a free tool called **ffmpeg**:

1. Install it by running `winget install ffmpeg` in the terminal, then close and reopen the terminal (and activate the venv again).
2. Convert the file:

   ```powershell
   ffmpeg -i recording.m4a -ar 16000 -ac 1 recording.wav
   ```

---

## Step 8 (optional): Use a real speech model

The app can use **Whisper**, a free, open speech model. It runs on your own computer, and your recordings are never uploaded.

**Be aware:** Whisper hasn't been trained on Rohingya, so for now its English output will be rough or wrong. This step is useful for trying out the app and getting a starting point, not for real translations yet.

1. Install Whisper support (with the venv active):

   ```powershell
   python -m pip install -e ".[whisper]"
   ```

2. Make a copy of the settings file:

   ```powershell
   copy configs\default.toml configs\whisper.toml
   ```

3. Open `configs\whisper.toml` in a text editor (Notepad is fine). Under `[speech_translator]`, change the `backend` line to:

   ```toml
   backend = "whisper"
   ```

   Optionally, set `source_language = "bn"`. Bengali is the closest language Whisper knows, and the hint can help.

4. Run the app with your new settings:

   ```powershell
   rtranslate path\to\recording.wav --config configs\whisper.toml
   ```

The first run downloads the model (a few hundred megabytes), so it takes a while. Later runs start quickly and work offline.

**Shortcut:** `configs\models.toml` already has all the real models switched on: Whisper, plus the dictionary models described below. To use it, install everything with `python -m pip install -e ".[whisper,lexicon]"` (about 1 GB to download). Then choose that file in the app's **Settings**, or add `--config configs\models.toml` on the command line. The models themselves download on first use, about 3 GB in total.

---

## Using the app

Open the app by double-clicking `run.bat`, or by typing `rtranslate-gui` in a terminal with the venv active.

The app is meant to be simple for people who don't read English. There's a menu down the left with four sections, each with its own colour and picture. Every screen has **one big button** for its main job; anything else is a small text link underneath.

- **Speak (blue microphone):** tap the big microphone, speak Rohingya, and tap again to stop. The English appears in large text and is read aloud by a built-in Windows voice. Tap the blue speaker button to hear it again. A green **SURE** or orange **NOT SURE** label shows how confident the translation is; when it's orange, check with an interpreter. **Replay recording** plays the original Rohingya again, and **or open a recording** translates a WAV file instead. If the recording is a word that's in the dictionary, its picture card appears underneath.
- **Words (purple book):** the dictionary. Switch between **Cards** (pictures) and **Table** (a list you can sort by tapping a column heading) at the top right. Type in the search box, or tap the microphone next to it and say a word to find it. The coloured buttons filter by status:
  - **Verified** (green): enough different speakers agree (3 by default; a matching photo can count as one of them)
  - **Likely** (blue): two sources agree
  - **New** (grey): one person has said it
  - **Unclear** (orange): speakers said the same-sounding word means different things

  Tap a card, or double-click a row in the table, to open the word. There you can hear every speaker's recording and check the word against a photo.
- **Teach (green speech bubble):** a short three-step lesson, with a progress bar at the top and a big green **CONTINUE** button at the bottom.
  1. **What is it?** Tap the picture of the thing, or type the English word.
  2. **Say it in Rohingya.** Tap the microphone and say the word. The bars show it was recorded; **LISTEN** plays it back.
  3. **Who is speaking?** Fill in the **speaker ID** (a code like `S014`, never a real name) and the **consent ID** (pointing to the speaker's signed consent; see `data/README.md`). Optionally add a photo, then tap **SAVE**.

  A green banner shows what was saved and how far it's trusted now. **TEACH ANOTHER** starts the next word and keeps the speaker filled in. Pictures for step 1 come from the `data/prompts/` folder, named after what they show (for example `cooking_pot.jpg`).
- **See (orange camera):** tap **TAKE PICTURE** (the first tap starts the camera, the second takes the photo), or **or open a photo**. The app lists English words for what it sees; tap **TEACH** next to a word to go straight to the lesson for it.

**Settings** (bottom of the menu) chooses the settings file: `default.toml` for quick stand-ins, `models.toml` for the real models, or `demo.toml` for the demo data. It's also where you **export verified words** as training data.

Everything stays on your computer. Recordings you teach are saved in `data/lexicon/`. Speak recordings and photos are never saved; for photos, only the image model's verdict is kept.

With the default settings, the dictionary works with placeholder models. It only recognises recordings that are exact copies of each other, and photo checks never agree. To get real matching, choose `configs\models.toml` in Settings (see the shortcut above).

---

## Quick reference

To open the app, double-click `run.bat`.

To use the command line instead:

```powershell
# 1. Open a terminal in the project folder, then:
.venv\Scripts\Activate.ps1

# 2. Translate a recording, or work with the dictionary
rtranslate path\to\recording.wav
rlexicon list
```

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `py` is not recognized | Python isn't installed, or "Add to PATH" wasn't ticked. Run the installer again, choose **Modify**, and make sure it's added to PATH. |
| `No suitable Python runtime found` | The version you asked for isn't installed. Run `py --list` to see which versions you have. |
| "running scripts is disabled on this system" | See the fix in Step 4. |
| `rtranslate` is not recognized | The venv isn't active. Run `.venv\Scripts\Activate.ps1` and check that `(.venv)` appears on the prompt. |
| `No module named ...` | Run the install command from Step 5 again, with the venv active. |
| An error about the WAV file format | Convert the file with the ffmpeg command in Step 7. |
| `run.bat` says "Could not find Python" | Install Python 3.11 (Step 1), making sure "Add python.exe to PATH" is ticked. |
| `run.bat` window flashes and closes | Open a terminal in the folder (Step 2) and type `.\run.bat` to see the message. |
| The app says a model "needs: pip install ..." | You chose `models.toml` without installing the models. Run the install command from the shortcut in Step 8. |
| The webcam doesn't work | Close other apps using the camera. In Windows Settings → Privacy & security → Camera, allow desktop apps to use it. |
| The microphone doesn't record | Check it's plugged in, and in Windows Settings → Privacy & security → Microphone, allow desktop apps to use it. |
| The webcam works but nothing is recognised (all scores 0.00) | You're on the default settings, which use a placeholder image model. Open Settings and choose `configs\models.toml` (see the shortcut in Step 8). |
| The first photo check takes a long time | The first time, the image model downloads (about 800 MB), then prepares its word list (about 15 seconds). After that, each photo takes about a second. |
| Something is badly broken | Delete the `.venv` folder and start again from Step 3, or double-click `run.bat` to set it up again. This doesn't affect your recordings or the project files. |
