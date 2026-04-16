"""
IntentCast Module 7 — Text-to-Speech (Sarvam Bulbul v3)

Converts the reconstructed sentence into spoken audio using Sarvam's
Bulbul v3 TTS API, with pace and speaker tuned to the child's emotional
state so the output voice sounds empathetic rather than robotic.

Env var required: SARVAM_API_KEY
"""

import base64
import os
import tempfile

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SARVAM_TTS_ENDPOINT = "https://api.sarvam.ai/text-to-speech"
MODEL = "bulbul:v3"
OUTPUT_PATH = os.path.join(tempfile.gettempdir(), "intentcast_output.wav")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _select_voice(emotion_context: str) -> tuple[float, str]:
    """Pick pace and speaker based on the fused emotion context string."""
    ctx = emotion_context.lower() if emotion_context else ""

    if "urgent" in ctx or "frustrated" in ctx:
        return 1.2, "arjun"
    if "exhausted" in ctx or "tired" in ctx:
        return 0.75, "meera"
    if "scared" in ctx or "struggling" in ctx:
        return 0.85, "meera"
    return 1.0, "meera"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def synthesize(text: str, language: str, emotion_context: str) -> str:
    """Synthesize speech from text using Sarvam Bulbul v3.

    Args:
        text: The reconstructed sentence to speak.
        language: Language code (``"ta-IN"``, ``"hi-IN"``, ``"en-IN"``).
        emotion_context: Fused emotion string — used to tune pace & speaker.

    Returns:
        str: Path to the generated WAV file (``/tmp/intentcast_output.wav``),
             or an empty string on failure.
    """
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        print("[sarvam_tts] SARVAM_API_KEY not set — returning empty path.")
        return ""

    pace, speaker = _select_voice(emotion_context)

    try:
        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [text],
            "target_language_code": language,
            "speaker": speaker,
            "model": MODEL,
            "pace": pace,
            "enable_preprocessing": True,
        }

        response = requests.post(
            SARVAM_TTS_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()

        body = response.json()
        audio_b64 = body["audios"][0]
        audio_bytes = base64.b64decode(audio_b64)

        with open(OUTPUT_PATH, "wb") as f:
            f.write(audio_bytes)

        return OUTPUT_PATH

    except Exception as exc:
        print(f"[sarvam_tts] Synthesis failed: {exc}")
        return ""
