"""
IntentCast Module 3 — Speech-to-Text (Sarvam Saaras v3)

Sends a short WAV audio clip to the Sarvam AI speech-to-text REST API and
returns the transcript along with the auto-detected language code.

Uses codemix mode to handle Tamil / Hindi / English mixed speech —
the child may switch languages mid-sentence.

Env var required: SARVAM_API_KEY
"""

import os

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SARVAM_ENDPOINT = "https://api.sarvam.ai/speech-to-text"
MODEL = "saaras:v3"

_FALLBACK = {"transcript": "", "language": "unknown"}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def transcribe(audio_path: str) -> dict:
    """Transcribe a WAV audio file using Sarvam Saaras v3.

    Args:
        audio_path: Absolute or relative path to a WAV file
                    (16 kHz mono, 3–10 s).

    Returns:
        dict: ``{"transcript": "amma water வேணும்", "language": "ta-IN"}``
              or ``{"transcript": "", "language": "unknown"}`` on any failure.
    """
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        print("[sarvam_stt] SARVAM_API_KEY not set — returning fallback.")
        return dict(_FALLBACK)

    try:
        with open(audio_path, "rb") as audio_file:
            files = {
                "file": (os.path.basename(audio_path), audio_file, "audio/wav"),
            }
            data = {
                "model": MODEL,
                "language_code": "unknown",
                "mode": "codemix",
            }
            headers = {
                "api-subscription-key": api_key,
            }

            response = requests.post(
                SARVAM_ENDPOINT,
                headers=headers,
                files=files,
                data=data,
                timeout=15,
            )

        response.raise_for_status()
        body = response.json()

        return {
            "transcript": body.get("transcript", ""),
            "language": body.get("language_code", "unknown"),
        }

    except Exception as exc:
        err_msg = str(exc)
        if hasattr(exc, "response") and exc.response is not None:
             try:
                 err_msg = f"{exc.response.status_code} - {exc.response.text}"
             except:
                 pass
        print(f"[sarvam_stt] Transcription failed: {err_msg}")
        return {"transcript": f"STT API Error: {err_msg}", "language": "unknown"}
