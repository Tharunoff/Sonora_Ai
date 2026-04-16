"""
IntentCast Module 1 — Facial Emotion Analysis

Continuously analyzes live video frames for facial emotion in a background
daemon thread. The main server loop pushes frames in — this module processes
them without blocking anything.

Uses HSEmotion ONNX (enet_b0_8) for lightweight, low-latency emotion detection.
"""

import queue
import threading
import cv2
import numpy as np
from collections import deque

from hsemotion_onnx.facial_emotions import HSEmotionRecognizer

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
LATEST_EMOTION: dict = {"emotion": "neutral", "confidence": 0.0}

_frame_queue: queue.Queue | None = None


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------
def _analysis_loop(frame_queue: queue.Queue) -> None:
    """Blocking loop that pulls frames from the queue and runs HSEmotion ONNX."""
    global LATEST_EMOTION

    print("[IntentCast:FacialEmotion] Initializing HSEmotion ONNX...")
    # Load the fast B0 model
    model_name = 'enet_b0_8_best_vgaf'
    fer = HSEmotionRecognizer(model_name=model_name)
    
    # Haar Cascade is lightweight enough for our PWA latency requirements
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Smoothing window: 5 frames catches micro-expressions quickly without too much jitter
    recent_scores = deque(maxlen=5)

    print("[IntentCast:FacialEmotion] HSEmotion worker started.")

    while True:
        frame = frame_queue.get()  # blocks until a frame is available

        try:
            # OpenCV cascades expect grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # HSEmotion expects standard RGB
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Fast detection
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            
            if len(faces) > 0:
                # Use the first face detected
                (x1, y1, w, h) = faces[0]
                x2, y2 = x1 + w, y1 + h

                # Small padding to include some context (eyes/mouth border limits micro-expression loss)
                padding_x = int(w * 0.1)
                padding_y = int(h * 0.2)
                x1 = max(0, x1 - padding_x)
                y1 = max(0, y1 - padding_y)
                x2 = min(image_rgb.shape[1], x2 + padding_x)
                y2 = min(image_rgb.shape[0], y2 + padding_y)

                face_img = image_rgb[y1:y2, x1:x2, :]

                if np.prod(face_img.shape) > 0:
                    emotion, scores = fer.predict_emotions(face_img, logits=True)
                    recent_scores.append(scores)

                    # Smooth out the raw logits
                    smoothed_scores = np.mean(recent_scores, axis=0)
                    emotion_idx = np.argmax(smoothed_scores)
                    dominant = fer.idx_to_class[emotion_idx].lower()

                    # Convert logits to a pseudo-confidence (softmax)
                    shifted_scores = smoothed_scores - np.max(smoothed_scores)
                    exp_scores = np.exp(shifted_scores)
                    softmax_scores = exp_scores / exp_scores.sum()
                    confidence = softmax_scores[emotion_idx]

                    LATEST_EMOTION = {
                        "emotion": dominant,
                        "confidence": round(float(confidence), 2),
                    }
                    
        except Exception:
            # Revert to neutral on failure just like DeepFace version
            LATEST_EMOTION = {"emotion": "neutral", "confidence": 0.0}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def start_analysis(frame_queue: queue.Queue) -> None:
    """Start the background daemon thread that consumes frames from *frame_queue*."""
    global _frame_queue
    _frame_queue = frame_queue

    worker = threading.Thread(target=_analysis_loop, args=(frame_queue,), daemon=True)
    worker.start()


def push_frame(frame) -> None:
    """Push a video frame into the analysis queue (non-blocking).

    If the queue is full (maxsize=1), the old frame is silently dropped
    and replaced with this one so the model always processes the freshest frame.
    """
    if _frame_queue is None:
        return

    # Drop the stale frame (if any) and put the fresh one
    try:
        _frame_queue.get_nowait()
    except queue.Empty:
        pass

    try:
        _frame_queue.put_nowait(frame)
    except queue.Full:
        pass


def get_latest_emotion() -> dict:
    """Return the most recent emotion analysis result.

    Returns:
        dict: ``{"emotion": "sad", "confidence": 0.87}``
              or ``{"emotion": "neutral", "confidence": 0.0}`` when no face
              has been detected yet.
    """
    return LATEST_EMOTION
