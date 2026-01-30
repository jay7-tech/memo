#!/bin/bash
# MEMO Launcher for Raspberry Pi (Bookworm/Bullseye compatible)

echo "[MEMO] Starting..."
echo "[MEMO] Activating virtual environment..."
source venv/bin/activate

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "[MEMO] Starting Ollama AI Service..."
    ollama serve &
    OLLAMA_PID=$!
    echo "[MEMO] Waiting for AI to wake up..."
    # Wait loop
    until curl -s http://localhost:11434/api/tags >/dev/null; do
        sleep 1
    done
    echo "[MEMO] AI Service Ready!"
else
    echo "[MEMO] AI Service already active."
fi

# Check if libcamerify exists (needed for Bookworm OS to us OpenCV)
if command -v libcamerify &> /dev/null; then
    echo "[MEMO] Detected libcamera system. Using libcamerify wrapper."
    libcamerify python main.py
else
    echo "[MEMO] Legacy camera system detected. Standard launch."
    python main.py
fi
