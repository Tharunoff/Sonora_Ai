import asyncio
import base64
import json
import logging
import os
import tempfile
import time
from typing import Dict, Any

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from hsemotion_onnx.facial_emotions import HSEmotionRecognizer

# Import the existing modules
import acoustic_analyzer
import sarvam_stt
import intent_llm
import sarvam_tts

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IntentCast.Backend")

app = FastAPI(title="IntentCast Backend", description="Real-time AAC API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    logger.info("Loading HSEmotionONNX model...")
    fer = HSEmotionRecognizer(model_name='enet_b0_8_best_vgaf')
except Exception as e:
    logger.error(f"Failed to load HSEmotionONNX: {e}")
    fer = None

# --- Asynchronous Wrapper Functions ---

async def run_visual_emotion(face_crop_b64: str) -> str:
    """Function C: Run face crop through HSEmotionONNX for Visual Emotion."""
    if not fer or not face_crop_b64:
        return "Neutral"
    
    def _process():
        try:
            if "base64," in face_crop_b64:
                b64_data = face_crop_b64.split("base64,")[1]
            else:
                b64_data = face_crop_b64
                
            img_bytes = base64.b64decode(b64_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return "Neutral"
            
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            emotion, _ = fer.predict_emotions(img_rgb, logits=False)
            return emotion.capitalize()
        except Exception as e:
            logger.error(f"Visual emotion error: {e}")
            return "Neutral"
            
    return await asyncio.to_thread(_process)

async def run_acoustic_emotion(audio_path: str) -> str:
    """Function B: Run audio through librosa for Acoustic Urgency/Emotion."""
    if not os.path.exists(audio_path):
        return "Neutral"

    # Analyze acoustic urgency using local librosa
    res = await asyncio.to_thread(acoustic_analyzer.analyze, audio_path)
    return res.get("urgency", "Neutral").capitalize()

async def run_speech_to_text(audio_path: str) -> Dict[str, str]:
    """Function A: Convert to WAV then run through Sarvam STT."""
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        return {"transcript": "", "language": "unknown"}

    def _convert_and_transcribe():
        # Use a sibling temp file for WAV (avoids .webm → .wav path collision issues)
        wav_path = audio_path + ".converted.wav"
        try:
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(audio_path)
                duration_s = len(audio) / 1000.0
                logger.info(f"[STT] Audio duration: {duration_s:.2f}s, converting to 16kHz mono WAV")
                audio = audio.set_frame_rate(16000).set_channels(1)
                audio.export(wav_path, format="wav")
            except Exception as conv_err:
                import shutil
                shutil.copy(audio_path, wav_path)
                logger.warning(f"[STT] pydub conversion failed ({conv_err}), sending raw copy")

            result = sarvam_stt.transcribe(wav_path)
            return result
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

    return await asyncio.to_thread(_convert_and_transcribe)


# --- WebSocket Endpoint ---

class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Client connected.")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("Client disconnected.")

manager = ConnectionManager()

@app.websocket("/ws")
@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 1. FastAPI WebSocket receives [AudioBlob, MediaPipe_JSON]
            # Supported as a unified JSON for simple async processing:
            # { "audio_b64": "...", "face_crop_b64": "...", "gesture": "...", "language": "en-IN", "hf_token": "..." }
            message = await websocket.receive_text()
            payload = json.loads(message)
            
            audio_b64 = payload.get("audio_b64", "")
            face_crop_b64 = payload.get("face_crop_b64", "")
            gesture = payload.get("gesture", "None")
            target_language = payload.get("language", "ta-IN")
            
            # Dynamically set API keys from frontend settings
            config = payload.get("config", {})
            if config.get("gemini_api_key"):
                os.environ["GEMINI_API_KEY"] = config["gemini_api_key"]
            if config.get("sarvam_api_key"):
                os.environ["SARVAM_API_KEY"] = config["sarvam_api_key"]

            start_time = time.time()
            
            # Save raw browser audio to temp file (webm/ogg)
            fd, audio_path = tempfile.mkstemp(suffix=".webm")
            os.close(fd)

            
            try:
                if "base64," in audio_b64:
                    audio_b64 = audio_b64.split("base64,")[1]
                with open(audio_path, 'wb') as f:
                    f.write(base64.b64decode(audio_b64))
            except Exception as e:
                logger.error(f"Error saving audio blob: {e}")
                pass

            # 2. asyncio.gather() runs three functions simultaneously
            stt_task = run_speech_to_text(audio_path)
            acoustic_task = run_acoustic_emotion(audio_path)
            visual_task = run_visual_emotion(face_crop_b64)

            stt_res, acoustic_emotion, visual_emotion = await asyncio.gather(
                stt_task, acoustic_task, visual_task
            )

            # Cleanup temp audio
            if os.path.exists(audio_path):
                os.remove(audio_path)

            # 3. Merge outputs into a dictionary
            transcript = stt_res.get("transcript", "")
            detected_language = stt_res.get("language", target_language)
            if detected_language == "unknown":
                detected_language = target_language

            # Construct Emotion Context
            emotion_context = f"Visual Emotion: {visual_emotion}. Acoustic Emotion: {acoustic_emotion}. Gesture Detected: {gesture}."
            
            merged_data = {
                "transcript": transcript,
                "visual_emotion": visual_emotion,
                "acoustic_emotion": acoustic_emotion,
                "gesture": gesture,
                "emotion_context": emotion_context,
                "language": detected_language
            }
            logger.info(f"Merged Outputs: {merged_data}")

            # ⚡ LIVE TELEMETRY: Send STT + emotion data immediately, BEFORE LLM/TTS
            await websocket.send_json({
                "type": "stt_result",
                "transcript": transcript,
                "visual_emotion": visual_emotion,
                "acoustic_emotion": acoustic_emotion,
                "gesture": gesture,
                "emotion_context": emotion_context,
                "language": detected_language,
                "latency_sec": time.time() - start_time
            })

            # 4. Pass dictionary to Gemini 1.5 Flash to reconstruct sentence
            llm_res = await asyncio.to_thread(
                intent_llm.reconstruct, transcript, emotion_context, detected_language
            )
            reconstructed_sentence = llm_res.get("reconstructed", transcript)
            logger.info(f"Reconstructed Intent: {reconstructed_sentence}")

            # 5. Pass Gemini's output + Target Language to Sarvam TTS
            audio_url_or_path = await asyncio.to_thread(
                sarvam_tts.synthesize, reconstructed_sentence, detected_language, emotion_context
            )

            tts_audio_b64 = ""
            if audio_url_or_path and os.path.exists(audio_url_or_path):
                with open(audio_url_or_path, "rb") as f:
                    tts_audio_b64 = base64.b64encode(f.read()).decode("utf-8")

            latency = time.time() - start_time
            logger.info(f"Pipeline completed in {latency:.2f}s")

            # Send back to client
            await websocket.send_json({
                "type": "result",
                "transcript": transcript,
                "reconstructed": reconstructed_sentence,
                "emotion_context": emotion_context,
                "audio_url": audio_url_or_path, # fallback for traditional url
                "audio_b64": tts_audio_b64,
                "latency_sec": latency
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket Error: {str(e)}")
        manager.disconnect(websocket)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
