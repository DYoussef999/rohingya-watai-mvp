"""Image input for the lexicon: files and the camera. Images are RGB uint8 arrays (H x W x 3).

Uses OpenCV (Apache 2.0), installed with ``pip install -e ".[lexicon]"``.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Self

import numpy as np


def _cv2():
    try:
        import cv2
    except ImportError as e:
        raise ImportError('images and the webcam need: pip install -e ".[lexicon]"') from e
    return cv2


def load_image(path: str | Path) -> np.ndarray:
    """Read a JPEG/PNG/... file as RGB."""
    cv2 = _cv2()
    # imdecode instead of imread so paths with non-ASCII characters work on Windows.
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"{path}: not a readable image")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


class Camera:
    """An open webcam. Frames stay in memory only; nothing is written to disk."""

    def __init__(self, index: int = 0) -> None:
        cv2 = _cv2()
        self._cv2 = cv2
        self._cap = cv2.VideoCapture(index)
        if not self._cap.isOpened():
            self._cap.release()
            raise RuntimeError(
                f"webcam {index} could not be opened. Close other apps using it, and check "
                "Windows Settings > Privacy & security > Camera."
            )

    def read(self) -> np.ndarray | None:
        """The next frame as RGB, or None if the camera gave nothing."""
        ok, frame = self._cap.read()
        return self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB) if ok else None

    def close(self) -> None:
        self._cap.release()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def exposure_settled(brightness: list[float], window: int = 5, tolerance: float = 3.0) -> bool:
    """True once the last ``window`` frames' mean brightness varies by at most ``tolerance``.

    Webcams start over- or under-exposed and adjust over the first second or so;
    a photo taken before then is washed out.
    """
    recent = brightness[-window:]
    return len(recent) == window and max(recent) - min(recent) <= tolerance


def capture_frame(camera: int = 0, min_wait_s: float = 0.5, max_wait_s: float = 4.0) -> np.ndarray:
    """Take one photo, waiting until the camera's exposure has settled."""
    with Camera(camera) as cam:
        start = time.monotonic()
        frame, brightness = None, []
        while time.monotonic() - start < max_wait_s:
            latest = cam.read()
            if latest is None:
                continue
            frame = latest
            brightness.append(float(frame.mean()))
            if time.monotonic() - start >= min_wait_s and exposure_settled(brightness):
                break
        if frame is None:
            raise RuntimeError(f"webcam {camera} returned no image")
        return frame


def to_png_base64(image: np.ndarray, max_width: int | None = None) -> str:
    """Encode for display (Tk's PhotoImage reads base64 PNG), optionally shrunk to fit."""
    cv2 = _cv2()
    if max_width and image.shape[1] > max_width:
        height = round(image.shape[0] * max_width / image.shape[1])
        image = cv2.resize(image, (max_width, height), interpolation=cv2.INTER_AREA)
    ok, png = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if not ok:
        raise ValueError("could not encode image")
    return base64.b64encode(png.tobytes()).decode("ascii")
