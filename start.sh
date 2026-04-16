#!/bin/bash
echo "Starting IntentCast..."

# Check .env exists
if [ ! -f .env ]; then
  echo "ERROR: .env file not found"
  echo "Copy .env.example to .env and add your API keys"
  exit 1
fi

# Download gesture model if not present
if [ ! -f gesture_recognizer.task ]; then
  echo "Downloading MediaPipe gesture model..."
  curl -L -o gesture_recognizer.task \
    "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
fi

# Start backend in background
echo "Starting FastAPI backend on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "Starting React frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "IntentCast is running!"
echo "Open: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop everything"

# Kill both on Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
