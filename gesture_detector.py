"""
IntentCast Module 2 — Hand Gesture Detection

Uses MediaPipe Gesture Recognizer in LIVE_STREAM mode with an async result
callback. Frames are submitted via process_frame(); the latest detected
gesture is available instantly from get_latest_gesture().

The gesture_recognizer.task model is auto-downloaded on first initialize().
"""

import os
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    GestureRecognizer,
    GestureRecognizerOptions,
    GestureRecognizerResult,
    RunningMode,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
)
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "gesture_recognizer.task"
)

GESTURE_MAP = {
    "Pointing_Up":  "wants something above",
    "Open_Palm":    "stop / no / reject",
    "Thumb_Up":     "yes / good / agree",
    "Thumb_Down":   "no / bad / disagree",
    "Closed_Fist":  "frustrated / in pain",
    "Victory":      "help me / urgent",
    "ILoveYou":     "love / comfort needed",
}

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
LATEST_GESTURE: dict = {"gesture": "no gesture", "raw": None}

_recognizer: GestureRecognizer | None = None


# ---------------------------------------------------------------------------
# Async callback (invoked by MediaPipe on its own thread)
# ---------------------------------------------------------------------------
def _on_result(
    result: GestureRecognizerResult,
    output_image: mp.Image,
    timestamp_ms: int,
) -> None:
    """Called by MediaPipe when a LIVE_STREAM frame has been processed."""
    global LATEST_GESTURE

    try:
        if result.gestures and len(result.gestures) > 0:
            top = result.gestures[0][0]  # highest-confidence gesture
            raw = top.category_name
            LATEST_GESTURE = {
                "gesture": GESTURE_MAP.get(raw, "no gesture"),
                "raw": raw,
            }
        else:
            LATEST_GESTURE = {"gesture": "no gesture", "raw": None}
    except Exception:
        LATEST_GESTURE = {"gesture": "no gesture", "raw": None}


# ---------------------------------------------------------------------------
# Model download helper
def _download_model() -> None:
    """Download gesture_recognizer.task if it isn't already cached locally."""
    print("[gesture_detector] Forcing model redownload...")
    if os.path.exists(MODEL_PATH):
        os.remove(MODEL_PATH)
        
    print(f"[gesture_detector] Downloading model to {MODEL_PATH} …")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("[gesture_detector] Model downloaded.")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def initialize() -> None:
    """Download the model (if needed) and create the LIVE_STREAM recognizer.

    Call once at server startup.
    """
    global _recognizer

    _download_model()

    options = GestureRecognizerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.LIVE_STREAM,
        result_callback=_on_result,
    )
    _recognizer = GestureRecognizer.create_from_options(options)


def process_frame(frame, timestamp_ms: int) -> None:
    """Submit a BGR video frame for asynchronous gesture recognition.

    Args:
        frame: numpy array in BGR format (as captured by OpenCV).
        timestamp_ms: Monotonically increasing timestamp in milliseconds.
                      Use ``int(time.time() * 1000)``.
    """
    if _recognizer is None:
        return

    try:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        _recognizer.recognize_async(mp_image, timestamp_ms)
    except Exception:
        pass  # Frame skipped — next one will arrive in 500ms


def get_latest_gesture() -> dict:
    """Return the most recent gesture detection result.

    Returns:
        dict: ``{"gesture": "wants something above", "raw": "Pointing_Up"}``
              or ``{"gesture": "no gesture", "raw": None}`` when no hand
              gesture is detected.
    """
    return LATEST_GESTURE
