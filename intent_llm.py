"""
IntentCast Module 6 — Intent Reconstruction (Gemini 2.5 Flash)

Takes fragmented speech, an emotion context string, and a language code,
then asks Gemini to reconstruct what the child intended to say as a single
natural sentence in the detected language.

Env var required: GEMINI_API_KEY
Install: pip install google-generativeai
"""

import os
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "You are an AI communication assistant helping a non-verbal or speech-impaired child "
    "communicate their needs to caregivers.\n\n"
    "Your job is to reconstruct what the child intended to say as a single, "
    "simple, natural sentence — the way a child would actually say it.\n\n"
    "Rules:\n"
    "- Output ONLY the reconstructed sentence. Nothing else.\n"
    "- Keep it short (under 15 words)\n"
    "- Match the language of the transcript:\n"
    "  ta-IN → respond in Tamil\n"
    "  hi-IN → respond in Hindi\n"
    "  en-IN → respond in English\n"
    "- If mixed language detected, use the dominant one\n"
    "- Sound like a child, not a robot"
)

_USER_TEMPLATE = (
    'Speech fragments heard: "{transcript}"\n'
    'Emotional state: "{emotion_context}"\n'
    'Detected language: "{language}"\n\n'
    "What is this child trying to say?"
)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def reconstruct(transcript: str, emotion_context: str, language: str) -> dict:
    """Reconstruct the child's intended sentence using Gemini 2.5 Flash.

    Args:
        transcript: Raw fragmented speech from Sarvam STT.
        emotion_context: Fused emotion string from emotion_fusion.fuse().
        language: Detected language code (``"ta-IN"``, ``"hi-IN"``, ``"en-IN"``).

    Returns:
        dict: ``{"reconstructed": "அம்மா தண்ணீர் வேணும்", "language": "ta-IN"}``
              or the transcript unchanged on any failure.
    """
    fallback = {"reconstructed": transcript, "language": language}

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[intent_llm] GEMINI_API_KEY not set — will return transcript unchanged.")
        return fallback

    try:
        client = genai.Client(api_key=api_key)

        user_prompt = _USER_TEMPLATE.format(
            transcript=transcript,
            emotion_context=emotion_context,
            language=language,
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            )
        )
        
        reconstructed = response.text.strip() if response.text else ""

        if not reconstructed:
            return fallback

        return {"reconstructed": reconstructed, "language": language}

    except Exception as exc:
        print(f"[intent_llm] Gemini call failed: {exc}")
        return fallback
