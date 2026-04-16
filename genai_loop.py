import os
import asyncio
import base64
import httpx
from google import genai
from google.genai import types

SYSTEM_PROMPT = """You are the core intelligence of IntentCast, a real-time multimodal AAC system for stroke patients.
You will be provided a 'Consensus State' composed of acoustic energy metrics, eye aspect ratios (EAR), and facial analysis.
Your job is to reconstruct a single, 1-sentence intent of what the patient most likely wants or feels. 
Follow these STRICT rules:
1. Output ONLY the reconstructed sentence. Nothing else.
2. If metrics indicate silence and closed eyes, output "I am resting."
3. If metrics indicate acoustic agitation and high EAR (surprise/fear), output "I need immediate assistance!"
4. Keep the sentence under 10 words.
"""

async def reconstruct_intent(consensus_state: str, gemini_key: str = "") -> str:
    """Async call to Gemini 1.5 Flash applying Semantic Fallback capabilities."""
    api_key_to_use = gemini_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key_to_use:
        return "I need assistance. (No API Key)"
        
    try:
        client = genai.Client(api_key=api_key_to_use)
        
        response = await client.aio.models.generate_content(
            model="gemini-1.5-flash",
            contents=consensus_state,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            )
        )
        output = response.text.strip() if response.text else ""
        return output if output else "I need assistance."
    except Exception as e:
        print(f"Gemini Error (Applying Guardrail Fallback): {e}")
        return "I need assistance." 

async def synthesize_speech(text: str, sarvam_key: str = "") -> bytes:
    """Pipe text into Sarvam Bulbul TTS async API and retrieve audio bytes."""
    api_key_to_use = sarvam_key or os.environ.get("SARVAM_API_KEY", "")
    if not api_key_to_use:
        return b""
        
    url = "https://api.sarvam.ai/text-to-speech"
    
    headers = {
        "api-subscription-key": api_key_to_use,
        "Content-Type": "application/json"
    }
    
    # Using Sarvam's standard payload format
    payload = {
        "inputs": [text],
        "target_language_code": "en-IN", 
        "speaker": "meera",
        "pitch": 0,
        "pace": 1.0,
        "loudness": 1.5,
        "speech_sample_rate": 8000,
        "enable_preprocessing": True,
        "model": "bulbul:v1"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            
            data = res.json()
            audios = data.get("audios", [])
            if audios:
                # sarvam returns base64 encoded strings in 'audios' list
                return base64.b64decode(audios[0])
            return b""
    except Exception as e:
        print(f"Sarvam TTS Error: {e}")
        return b""

async def run_generative_loop(consensus_state: str, gemini_key: str = "", sarvam_key: str = "") -> dict:
    """
    Executes the Generative Loop: Consensus -> Gemini Flash -> Intent -> Sarvam TTS -> Bytes
    """
    intent_text = await reconstruct_intent(consensus_state, gemini_key)
    audio_bytes = await synthesize_speech(intent_text, sarvam_key)
    
    return {
        "reconstructed_intent": intent_text,
        "audio_bytes": audio_bytes
    }
