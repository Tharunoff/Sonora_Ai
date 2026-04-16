"""
IntentCast Module 5 — Emotion Fusion

Pure Python logic that merges face, acoustic, and gesture signals into a
single human-readable emotion context string for the LLM prompt.
No ML. Under 60 lines.
"""


def fuse(face_result: dict, acoustic_result: dict, gesture_result: dict) -> str:
    """Fuse multimodal signals into one emotion context string.

    Returns:
        str: e.g. ``"sad and exhausted, pointing upward"``
    """
    face = face_result.get("emotion", "neutral")
    confidence = face_result.get("confidence", 0.0)
    urgency = acoustic_result.get("urgency", "neutral")
    energy = acoustic_result.get("energy", 0.0)
    gesture = gesture_result.get("gesture", "no gesture")

    # --- Special overrides (checked first) ---
    if face == "fear" and energy < 0.3:
        primary = "scared and struggling"
    elif face == "sad" and urgency == "exhausted":
        primary = "deeply tired"
    elif face == "angry" and urgency == "urgent":
        primary = "frustrated and urgent"
    # --- Standard priority logic ---
    elif confidence > 0.6:
        primary = f"{face} and {urgency}" if urgency != "neutral" else face
    else:
        primary = urgency if urgency != "neutral" else face

    # --- Gesture always appended ---
    if gesture == "no gesture":
        context = f"{primary}, no gesture detected"
    else:
        context = f"{primary}, {gesture}"

    # --- Rejection override: prepend "refusing: " ---
    if gesture == "stop / no / reject":
        context = f"refusing: {primary}, rejecting something"

    return context
