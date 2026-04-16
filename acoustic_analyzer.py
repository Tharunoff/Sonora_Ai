"""
IntentCast Module 4 — Acoustic Signal Analysis

Pure librosa signal processing — no ML model. Extracts energy, pace, and
pitch variance from a short WAV clip and maps them to a human-readable
urgency label that the emotion fusion layer can consume.

SenseVoice fine-tuning (Module 11) will replace this later; for now librosa
gives a solid baseline for detecting urgent / exhausted / distressed states.

Install: pip install librosa soundfile
"""

import numpy as np
import librosa


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_SAMPLE_RATE = 22050  # librosa default; resampled on load
_FALLBACK = {
    "urgency": "neutral",
    "energy": 0.0,
    "pace": 0,
    "pitch_variance": 0.0,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _compute_energy(y: np.ndarray) -> float:
    """Mean RMS energy, clamped to 0.0–1.0."""
    rms = librosa.feature.rms(y=y)[0]
    mean_rms = float(np.mean(rms))
    # Normalize: typical speech RMS peaks around 0.1–0.3 after librosa load.
    # Scale so that 0.25 maps to roughly 1.0.
    normalized = min(mean_rms / 0.25, 1.0)
    return round(normalized, 2)


def _compute_pace(y: np.ndarray, sr: int) -> int:
    """Estimate syllable-rate proxy as onsets-per-second × 3 → ~WPM."""
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    duration = librosa.get_duration(y=y, sr=sr)
    if duration < 0.1:
        return 0
    onsets_per_sec = len(onsets) / duration
    # Rough heuristic: each onset ≈ 1 syllable, average word ≈ 3 syllables
    # so multiply by 60 to get per-minute, divide by 3 for words.
    # Simplified: onsets_per_sec * 60 gives syllables/min;
    # we keep that as the "pace" proxy (matches the >180 / <100 thresholds).
    pace = int(onsets_per_sec * 60)
    return pace


def _compute_pitch_variance(y: np.ndarray, sr: int) -> float:
    """Standard deviation of F0 via YIN, normalized to 0.0–1.0."""
    try:
        f0 = librosa.yin(y, fmin=80, fmax=600, sr=sr)
        # Filter out zeros / NaN (unvoiced segments)
        voiced = f0[(f0 > 0) & np.isfinite(f0)]
        if len(voiced) < 2:
            return 0.0
        std = float(np.std(voiced))
        # Normalize: typical child speech F0 std is 20–80 Hz.
        # Map 80 Hz std → 1.0.
        normalized = min(std / 80.0, 1.0)
        return round(normalized, 2)
    except Exception:
        return 0.0


def _classify_urgency(energy: float, pace: int, pitch_variance: float) -> str:
    """Map acoustic features to a human-readable urgency label."""
    if energy > 0.7 and pace > 180:
        return "urgent"
    if energy < 0.3 and pace < 100:
        return "exhausted"
    if pitch_variance > 0.6:
        return "distressed"
    return "neutral"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def analyze(audio_path: str) -> dict:
    """Analyze a short WAV clip for acoustic urgency signals.

    Args:
        audio_path: Path to a WAV file (any sample rate — librosa resamples).

    Returns:
        dict: ``{"urgency": "urgent", "energy": 0.82, "pace": 210,
                  "pitch_variance": 0.65}``
              or neutral fallback on any error.
    """
    try:
        y, sr = librosa.load(audio_path, sr=_SAMPLE_RATE, mono=True)

        if len(y) == 0:
            return dict(_FALLBACK)

        energy = _compute_energy(y)
        pace = _compute_pace(y, sr)
        pitch_variance = _compute_pitch_variance(y, sr)
        urgency = _classify_urgency(energy, pace, pitch_variance)

        return {
            "urgency": urgency,
            "energy": energy,
            "pace": pace,
            "pitch_variance": pitch_variance,
        }

    except Exception as exc:
        print(f"[acoustic_analyzer] Analysis failed: {exc}")
        return dict(_FALLBACK)
