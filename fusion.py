import base64
import os
import tempfile
import librosa
import numpy as np

def calculate_audio_features(audio_b64: str) -> float:
    """
    Decodes a base64 webm/wav audio chunk, saves temporarily,
    and calculates RMS energy using librosa.
    """
    if "base64," in audio_b64:
        audio_b64 = audio_b64.split("base64,")[1]
    
    try:
        audio_bytes = base64.b64decode(audio_b64)
    except Exception as e:
        print(f"Error decoding base64: {e}")
        return 0.0

    fd, temp_path = tempfile.mkstemp(suffix=".webm")
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(audio_bytes)
            
        # load audio using librosa
        y, sr = librosa.load(temp_path, sr=None)
        
        if len(y) == 0:
            return 0.0
            
        # Calculate RMS energy
        rms = librosa.feature.rms(y=y)
        mean_rms = float(np.mean(rms))
        return mean_rms
    except Exception as e:
        print(f"Error processing audio in librosa: {e}")
        return 0.0
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

def generate_consensus_state(ear: float, rms: float, coordinates: list) -> str:
    """
    Merges Eye Aspect Ratio, RMS acoustic energy, and generalized facial state 
    into a structured Consensus State string.
    """
    ear = float(ear)
    
    # Simple gaze direction / eye openness heuristic
    if ear < 0.2:
        gaze_state = "Eyes Closed (Possible distress or fatigue)"
    elif ear > 0.35:
        gaze_state = "Eyes Wide Open (Possible surprise or alarm)"
    else:
        gaze_state = "Eyes Normal/Focused on standard plane"
        
    # Tone/Volume acoustic heuristic
    if rms > 0.1:
        acoustic_state = "Loud Vocalization/Agitation detected"
    elif rms > 0.02:
        acoustic_state = "Normal speech volume"
    elif rms > 0.005:
        acoustic_state = "Quiet mumbling/whispering"
    else:
        acoustic_state = "Silent"
        
    # Generalized facial heuristic based on coordinate count
    face_state = "Face locked (478 pts active)" if coordinates and len(coordinates) >= 470 else "Face lost or degraded"

    consensus = (
        f"[CONSENSUS STATE]\n"
        f"- Gaze/Eyes: {gaze_state} (EAR: {ear:.3f})\n"
        f"- Acoustic Energy: {acoustic_state} (RMS: {rms:.4f})\n"
        f"- Facial Detail: {face_state}\n"
    )
    return consensus

def process_edge_payload(payload_data: dict) -> str:
    """
    Entry point for the ProcessPoolExecutor.
    Extracts metrics and base64 audio, runs librosa, and yields the consensus.
    """
    metrics = payload_data.get("metrics", {})
    data = payload_data.get("data", {})
    
    ear = float(metrics.get("ear", 0.0))
    audio_b64 = data.get("audio_chunk_b64", "")
    coordinates = data.get("coordinates", [])
    
    rms_energy = 0.0
    if audio_b64:
        rms_energy = calculate_audio_features(audio_b64)
        
    consensus_string = generate_consensus_state(ear, rms_energy, coordinates)
    return consensus_string
