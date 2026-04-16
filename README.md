# IntentCast Setup
  
## Quick Start
1. pip install -r requirements.txt
2. cp .env.example .env
3. Add your API keys to .env
4. cd frontend && npm install
5. bash start.sh (Mac/Linux) or double-click start.bat (Windows)

## API Keys Needed
- SARVAM_API_KEY: Get from https://dashboard.sarvam.ai
- GEMINI_API_KEY: Get from https://aistudio.google.com/apikey (free)

## Folder Structure
intentcast/
├── .env                  ← your API keys (never share this)
├── .env.example          ← template (safe to share)
├── requirements.txt
├── start.sh
├── start.bat
├── main.py               ← FastAPI backend
├── facial_emotion.py
├── gesture_detector.py
├── sarvam_stt.py
├── acoustic_analyzer.py
├── emotion_fusion.py
├── intent_llm.py
├── sarvam_tts.py
├── gesture_recognizer.task
└── frontend/             ← React PWA
    ├── src/App.jsx
    ├── public/manifest.json
    └── .env
