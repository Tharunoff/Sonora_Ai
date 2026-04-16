@echo off
echo Starting IntentCast...
if not exist .env (
  echo ERROR: .env file not found
  echo Copy .env.example to .env and add your API keys
  pause
  exit /b
)
start "IntentCast Backend" uvicorn main:app --host 0.0.0.0 --port 8000
cd frontend
start "IntentCast Frontend" npm run dev
echo IntentCast is running at http://localhost:5173
pause
