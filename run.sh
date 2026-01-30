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

# Check if libcamerify exists AND we are using a Ribbon Camera (not USB)
# USB Webcams often crash with libcamerify on Bookworm
if command -v libcamerify &> /dev/null && ! ls /dev/video* &> /dev/null; then
    echo "[MEMO] Ribbon camera detected. Using libcamerify wrapper."
    libcamerify python main.py
else
    echo "[MEMO] USB Camera or Legacy system detected. Standard launch."
    # CLEANUP: Kill any lingering instances to prevent "Device busy" errors
    pkill -f "python main.py" 2>/dev/null
    python main.py
fi
