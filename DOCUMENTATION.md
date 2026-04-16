# IntentCast: Production-Grade Multimodal AAC System

## 1. Project Overview
**IntentCast** is an advanced Augmented and Alternative Communication (AAC) system designed specifically for children with speech impairments or non-verbal conditions. Unlike legacy AAC devices that rely on static buttons or robotic voices, IntentCast leverages **Fault-Tolerant Fusion**—merging fragmented speech, facial micro-expressions, body gestures, and acoustic energy into a single, cohesive intent.

The core goal is to reconstruct "junky" or unclear speech into grammatically perfect, emotionally tuned sentences in real-time.

---

## 2. System Architecture
The project follows a decoupled **Edge-Sensor + Parallel Inference** architecture.

### Phase 1: The Edge Sensors (Frontend)
- **Capture:** The React/Vite frontend serves as the sensory layer. It uses **MediaPipe** to track 478 facial landmarks and hand gestures.
- **Payload:** It packages a 1.5s audio blob and specific visual metadata (like face crops) into a unified JSON object.
- **Transport:** Data is blasted to the backend via a low-latency **WebSocket** bridge.

### Phase 2: Asynchronous Parallel Processing (Backend)
The FastAPI backend utilizes `asyncio.gather()` to run three intensive inference tasks simultaneously to maintain sub-1.5s latency:
1.  **Function A (Literal Transcript):** `Sarvam STT` (Saaras v3) attempts to find whatever literal fragments it can from the dysarthric speech.
2.  **Function B (Acoustic Context):** `SenseVoice` (via HuggingFace) analyzes the raw energy and "tone" of the sound to detect stress, urgency, or exhaustion.
3.  **Function C (Visual Context):** `HSEmotionONNX` runs inference on the face crop to identify micro-expressions (anger, sadness, joy).

### Phase 3: The Intent Engine (Gemini Flash)
The results from all three parallel streams are merged into a "Consensus State" and passed to **Gemini 1.5 Flash**. The LLM acts as an "Intent Reconstructor," using the visual/acoustic context to turn fragments like *"wa... ter..."* (with a "Urgent/Stressed" context) into *"I am very thirsty, I need water right now."*

### Phase 4: Emotion-Tuned Localization (Output)
The reconstructed intent is sent to **Sarvam TTS** (Bulbul v3). The system uses the detected emotion to tune the voice parameters (Pace/Speaker), generating a child-like, empathetic voice in the target language (Tamil, Hindi, or English).

---

## 3. Module Breakdown (Code Logic)

### Backend (`/`)
- `main.py`: The central nervous system. Manages WebSocket connections and orchestrates the parallel `asyncio` execution flow.
- `facial_emotion.py`: Implements `HSEmotionRecognizer`. It detects faces and predicts emotions using a lightweight ONNX model for high performance.
- `gesture_detector.py`: Uses MediaPipe's `GestureRecognizer` to identify specific signals like "Stop," "Thumbs Up," or "Pointing."
- `sarvam_stt.py`: Interfaces with Sarvam's Speech-to-Text API, specifically utilizing `codemix` mode for multilingual environments.
- `acoustic_analyzer.py`: A `librosa`-based fallback that calculates RMS energy and pitch variance if the SenseVoice API is unavailable.
- `emotion_fusion.py`: Pure logic that weighs the confidence of different signals. For example, if a child points at a "Stop" sign, it overrides the vocal transcript.
- `intent_llm.py`: Contains the system prompt for Gemini Flash. It ensures the reconstructed sentence sounds like a child and adheres to strict brevity rules.

### Frontend (`/frontend`)
- `src/hooks/useWebSocket.js`: A custom hook that manages the persistent connection to the FastAPI server and handles binary/JSON message discrimination.
- `src/components/Scanner.jsx`: (Logic implemented in Phase 2) The capture UI that displays the MediaPipe "skeleton" overlays and manages the `MediaRecorder` loop.

---

## 4. Case Scenarios (The Fusion Engine)

### Scenario A: The Urgent Request
- **Audio Transcript:** *"ah... ah..."* (Unclear)
- **Acoustic Emotion:** `<|URGENT|>` (High energy/volume)
- **Visual Emotion:** `Angry/Frustrated`
- **Gesture:** `Pointing Down`
- **LLM Context:** Fragment + Urgent + Frustrated + Pointing.
- **Intentcast Output:** "I need you to help me with this right now!" (Spoken in an assertive, fast-paced voice).

### Scenario B: The Tired Refusal
- **Audio Transcript:** *"no..."* (Weak/Whispered)
- **Acoustic Emotion:** `Exhausted` (Low energy)
- **Visual Emotion:** `Sad`
- **Gesture:** `Open Palm (Stop)`
- **Intentcast Output:** "I'm really tired, I don't want to do this anymore." (Spoken in a soft, slow-paced voice).

---

## 5. Setup & Installation

### Backend Setup
1.  **Python Version:** 3.10+
2.  **Install Dependencies:**
    ```bash
    pip install fastapi uvicorn requests librosa numpy opencv-python hsemotion-onnx google-genai mediapipe
    ```
3.  **Environment Variables (`.env`):**
    ```env
    SARVAM_API_KEY=your_key_here
    GEMINI_API_KEY=your_key_here
    ```
4.  **Run Server:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```

### Frontend Setup
1.  **Node Version:** 18+
2.  **Install:** `npm install`
3.  **Run:** `npm run dev`

---

## 6. Logic Flow Summary (The "Magic" Loop)
1. **CAPTURE:** Client sends `[Audio_B64, Face_Crop_B64, Gesture_Label]`
2. **PARALLEL:**
   - Task 1: `SarvamSTT(Audio)` -> "transcript"
   - Task 2: `SenseVoice(Audio)` -> "acoustic_emotion"
   - Task 3: `HSEmotion(Face)` -> "visual_emotion"
3. **MERGE:** Create metadata string: "Visual: Happy, Acoustic: Quiet, Gesture: Pointing"
4. **RECONSTRUCT:** `Gemini(transcript + metadata)` -> "final_sentence"
5. **SPEAK:** `SarvamTTS(final_sentence, emotion)` -> `WAV_Bytes`
6. **EMIT:** Return `JSON + Audio` to Client for instant playback.
