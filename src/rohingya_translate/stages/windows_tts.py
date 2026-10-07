"""English text-to-speech with the voices built into Windows (System.Speech, via PowerShell).

No extra packages and fully offline. Each call starts PowerShell, which adds
about a second; fine for reading one translation aloud.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from rohingya_translate.audio import SAMPLE_RATE, Audio, load_wav
from rohingya_translate.config import StageConfig

# Text and settings travel in environment variables, never inside the script,
# so nothing in the text can be run as a command.
SCRIPT = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
if ($env:RT_TTS_VOICE) {
    $match = $s.GetInstalledVoices() | Where-Object {
        $_.Enabled -and $_.VoiceInfo.Name -like "*$($env:RT_TTS_VOICE)*" } | Select-Object -First 1
    if ($match) { $s.SelectVoice($match.VoiceInfo.Name) }
}
$s.Rate = [int]$env:RT_TTS_RATE
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(
    [int]$env:RT_TTS_RATE_HZ, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
    [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile($env:RT_TTS_OUT, $format)
$s.Speak($env:RT_TTS_TEXT)
$s.Dispose()
"""


class WindowsSpeechBackend:
    """Implements Synthesizer.

    Options: ``voice`` (part of a voice name, e.g. "Zira") and ``rate`` (-10 to 10).
    """

    def __init__(self, config: StageConfig | None = None) -> None:
        if sys.platform != "win32":
            raise RuntimeError("the 'windows' voice only works on Windows")
        self.config = config or StageConfig()

    def synthesize(self, text: str) -> Audio:
        if not text.strip():
            return Audio(np.zeros(0, dtype=np.float32))
        fd, out = tempfile.mkstemp(suffix=".wav", prefix="rt_tts_")
        os.close(fd)
        env = dict(os.environ, RT_TTS_TEXT=text, RT_TTS_OUT=out,
                   RT_TTS_VOICE=str(self.config.options.get("voice", "")),
                   RT_TTS_RATE=str(int(self.config.options.get("rate", 0))),
                   RT_TTS_RATE_HZ=str(SAMPLE_RATE))
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
                env=env, check=True, capture_output=True, timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return load_wav(out)
        except (subprocess.SubprocessError, OSError) as e:
            raise RuntimeError("Windows could not read the text aloud") from e
        finally:
            Path(out).unlink(missing_ok=True)
